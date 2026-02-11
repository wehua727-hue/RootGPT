"""
Technical Question Detector - Detects programming-related questions
"""

import re
import logging
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TechnicalContext:
    """Technical context extracted from message"""
    primary_language: Optional[str] = None
    framework: Optional[str] = None
    topic: Optional[str] = None
    keywords: List[str] = None
    confidence: float = 0.0
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


@dataclass
class CodeSnippet:
    """Code snippet detected in message"""
    code: str
    language: Optional[str] = None
    line_count: int = 0
    has_error: bool = False


@dataclass
class ErrorInfo:
    """Error information extracted from message"""
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    language: Optional[str] = None


class TechnicalQuestionDetector:
    """Detects technical questions and extracts context"""
    
    # Programming languages
    LANGUAGES = {
        'python': ['python', 'py', 'django', 'flask', 'fastapi', 'pip', 'virtualenv', 'conda'],
        'javascript': ['javascript', 'js', 'node', 'nodejs', 'npm', 'yarn', 'react', 'vue', 'angular'],
        'typescript': ['typescript', 'ts', 'tsx'],
        'java': ['java', 'spring', 'maven', 'gradle', 'jvm'],
        'csharp': ['c#', 'csharp', 'dotnet', '.net', 'asp.net'],
        'go': ['golang', 'go'],
        'rust': ['rust', 'cargo'],
    }
    
    # Frameworks
    FRAMEWORKS = {
        'django': ['django', 'drf', 'django-rest-framework'],
        'fastapi': ['fastapi'],
        'flask': ['flask'],
        'react': ['react', 'reactjs', 'jsx', 'hooks', 'usestate', 'useeffect'],
        'nextjs': ['next.js', 'nextjs', 'next'],
        'vuejs': ['vue', 'vuejs', 'vue.js'],
        'nodejs': ['node', 'nodejs', 'express', 'expressjs'],
        'express': ['express', 'expressjs'],
    }
    
    # Tools and technologies
    TOOLS = {
        'docker': ['docker', 'dockerfile', 'container', 'image'],
        'git': ['git', 'github', 'gitlab', 'commit', 'branch', 'merge', 'pull request'],
        'postgresql': ['postgres', 'postgresql', 'psql'],
        'mongodb': ['mongo', 'mongodb', 'mongoose'],
        'redis': ['redis'],
        'mysql': ['mysql'],
        'kubernetes': ['kubernetes', 'k8s', 'kubectl', 'pod'],
    }
    
    # Technical terms
    TECH_TERMS = [
        'function', 'funksiya', 'class', 'klass', 'method', 'metod',
        'variable', 'o\'zgaruvchi', 'array', 'massiv', 'object', 'obyekt',
        'api', 'database', 'ma\'lumotlar bazasi', 'server', 'client',
        'error', 'xato', 'xatolik', 'bug', 'debug', 'test', 'testing',
        'import', 'export', 'module', 'modul', 'package', 'paket',
        'async', 'await', 'promise', 'callback', 'event', 'hodisa',
        'component', 'komponent', 'props', 'state', 'holat',
        'query', 'so\'rov', 'request', 'response', 'javob',
        'authentication', 'autentifikatsiya', 'authorization', 'ruxsat',
        'deployment', 'deploy', 'production', 'development',
    ]
    
    # Code patterns
    CODE_PATTERNS = [
        r'def\s+\w+\s*\(',  # Python function
        r'class\s+\w+',  # Class definition
        r'function\s+\w+\s*\(',  # JavaScript function
        r'const\s+\w+\s*=',  # JavaScript const
        r'let\s+\w+\s*=',  # JavaScript let
        r'import\s+',  # Import statement
        r'from\s+\w+\s+import',  # Python import
        r'require\s*\(',  # Node.js require
        r'@\w+',  # Decorator
        r'=>',  # Arrow function
        r'\w+\.\w+\(',  # Method call
    ]
    
    # Error patterns
    ERROR_PATTERNS = [
        r'Error:',
        r'Exception:',
        r'Traceback',
        r'TypeError',
        r'ValueError',
        r'AttributeError',
        r'IndexError',
        r'KeyError',
        r'SyntaxError',
        r'ReferenceError',
        r'at line \d+',
        r'File ".*", line \d+',
    ]
    
    def __init__(self):
        logger.info("TechnicalQuestionDetector initialized")
    
    async def is_technical_question(self, message_text: str) -> bool:
        """Determine if message contains technical content"""
        if not message_text:
            return False
        
        message_lower = message_text.lower()
        confidence = 0.0
        
        # Check for programming languages
        for lang, keywords in self.LANGUAGES.items():
            if any(keyword in message_lower for keyword in keywords):
                confidence += 0.3
                break
        
        # Check for frameworks
        for framework, keywords in self.FRAMEWORKS.items():
            if any(keyword in message_lower for keyword in keywords):
                confidence += 0.2
                break
        
        # Check for tools
        for tool, keywords in self.TOOLS.items():
            if any(keyword in message_lower for keyword in keywords):
                confidence += 0.15
                break
        
        # Check for technical terms
        tech_term_count = sum(1 for term in self.TECH_TERMS if term in message_lower)
        if tech_term_count > 0:
            confidence += min(0.2, tech_term_count * 0.05)
        
        # Check for code patterns
        code_pattern_count = sum(1 for pattern in self.CODE_PATTERNS if re.search(pattern, message_text))
        if code_pattern_count > 0:
            confidence += min(0.3, code_pattern_count * 0.1)
        
        # Check for error patterns
        error_pattern_count = sum(1 for pattern in self.ERROR_PATTERNS if re.search(pattern, message_text))
        if error_pattern_count > 0:
            confidence += min(0.2, error_pattern_count * 0.1)
        
        # Threshold for technical classification
        is_technical = confidence >= 0.4
        
        if is_technical:
            logger.info(f"Technical question detected with confidence {confidence:.2f}")
        
        return is_technical
    
    async def extract_technical_context(self, message_text: str) -> TechnicalContext:
        """Extract programming language, framework, and topic from message"""
        if not message_text:
            return TechnicalContext()
        
        message_lower = message_text.lower()
        context = TechnicalContext()
        keywords = []
        confidence = 0.0
        
        # Detect primary language
        for lang, lang_keywords in self.LANGUAGES.items():
            if any(keyword in message_lower for keyword in lang_keywords):
                context.primary_language = lang
                keywords.extend([kw for kw in lang_keywords if kw in message_lower])
                confidence += 0.3
                break
        
        # Detect framework
        for framework, fw_keywords in self.FRAMEWORKS.items():
            if any(keyword in message_lower for keyword in fw_keywords):
                context.framework = framework
                keywords.extend([kw for kw in fw_keywords if kw in message_lower])
                confidence += 0.2
                break
        
        # Detect topic from technical terms
        found_terms = [term for term in self.TECH_TERMS if term in message_lower]
        if found_terms:
            context.topic = found_terms[0]  # Use first found term as topic
            keywords.extend(found_terms[:3])  # Add up to 3 terms
            confidence += 0.2
        
        # Check for code patterns
        if any(re.search(pattern, message_text) for pattern in self.CODE_PATTERNS):
            confidence += 0.2
        
        # Check for error patterns
        if any(re.search(pattern, message_text) for pattern in self.ERROR_PATTERNS):
            confidence += 0.1
            if not context.topic:
                context.topic = "debugging"
        
        context.keywords = list(set(keywords))[:10]  # Unique keywords, max 10
        context.confidence = min(1.0, confidence)
        
        logger.info(f"Extracted context: lang={context.primary_language}, "
                   f"framework={context.framework}, topic={context.topic}, "
                   f"confidence={context.confidence:.2f}")
        
        return context
    
    async def detect_code_snippet(self, message_text: str) -> Optional[CodeSnippet]:
        """Detect and extract code snippets from message"""
        if not message_text:
            return None
        
        # Check for markdown code blocks
        code_block_pattern = r'```(\w+)?\n(.*?)\n```'
        matches = re.findall(code_block_pattern, message_text, re.DOTALL)
        
        if matches:
            language, code = matches[0]
            return CodeSnippet(
                code=code.strip(),
                language=language if language else None,
                line_count=len(code.strip().split('\n')),
                has_error=any(re.search(pattern, code) for pattern in self.ERROR_PATTERNS)
            )
        
        # Check for inline code patterns
        if any(re.search(pattern, message_text) for pattern in self.CODE_PATTERNS):
            # Extract lines that look like code
            lines = message_text.split('\n')
            code_lines = [line for line in lines if any(re.search(pattern, line) for pattern in self.CODE_PATTERNS)]
            
            if code_lines:
                code = '\n'.join(code_lines)
                return CodeSnippet(
                    code=code,
                    language=None,
                    line_count=len(code_lines),
                    has_error=any(re.search(pattern, code) for pattern in self.ERROR_PATTERNS)
                )
        
        return None
    
    async def detect_error_message(self, message_text: str) -> Optional[ErrorInfo]:
        """Detect and parse error messages or stack traces"""
        if not message_text:
            return None
        
        # Check for error patterns
        for pattern in self.ERROR_PATTERNS:
            match = re.search(pattern, message_text)
            if match:
                error_type = match.group(0)
                
                # Try to extract error message (next line after error type)
                lines = message_text.split('\n')
                error_line_idx = next((i for i, line in enumerate(lines) if error_type in line), None)
                
                error_message = ""
                stack_trace = None
                
                if error_line_idx is not None:
                    # Get error message (same line or next line)
                    if error_line_idx < len(lines):
                        error_message = lines[error_line_idx].strip()
                        if error_line_idx + 1 < len(lines):
                            error_message += " " + lines[error_line_idx + 1].strip()
                    
                    # Get stack trace (multiple lines after error)
                    if error_line_idx + 2 < len(lines):
                        stack_lines = lines[error_line_idx:min(error_line_idx + 10, len(lines))]
                        stack_trace = '\n'.join(stack_lines)
                
                # Detect language from error type
                language = None
                if any(err in error_type for err in ['TypeError', 'ValueError', 'AttributeError', 'IndexError', 'KeyError']):
                    language = 'python'
                elif any(err in error_type for err in ['ReferenceError', 'SyntaxError']):
                    language = 'javascript'
                
                return ErrorInfo(
                    error_type=error_type,
                    error_message=error_message,
                    stack_trace=stack_trace,
                    language=language
                )
        
        return None
