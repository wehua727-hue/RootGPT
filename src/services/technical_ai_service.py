"""
Technical AI Service - Specialized AI service for technical questions
"""

import logging
from typing import Optional

from .ai_service import AIService
from .technical_question_detector import TechnicalContext, CodeSnippet, ErrorInfo
from ..config import Config

logger = logging.getLogger(__name__)


class TechnicalAIService(AIService):
    """AI service specialized for technical questions"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        logger.info("TechnicalAIService initialized")
    
    async def generate_technical_response(
        self,
        user_question: str,
        technical_context: TechnicalContext,
        code_snippet: Optional[CodeSnippet] = None,
        error_info: Optional[ErrorInfo] = None
    ) -> str:
        """Generate AI response with technical prompt"""
        # Build specialized technical prompt
        prompt = self.build_technical_prompt(
            user_question,
            technical_context,
            code_snippet,
            error_info
        )
        
        # Generate response using parent class method
        response = await self.generate_response(prompt)
        
        return response
    
    def build_technical_prompt(
        self,
        user_question: str,
        technical_context: TechnicalContext,
        code_snippet: Optional[CodeSnippet],
        error_info: Optional[ErrorInfo]
    ) -> str:
        """Build specialized prompt for technical questions"""
        
        # Base technical prompt
        prompt = """Sen RootGPT - dasturlash va texnologiya bo'yicha professional AI yordamchisan.

MUHIM: HAR DOIM O'ZBEK TILIDA JAVOB BER! (ALWAYS respond in Uzbek language!)

TEXNIK BILIMLAR:
- Dasturlash tillari: Python, JavaScript, TypeScript, Go, Rust, Java, C#
- Frameworklar: Django, FastAPI, Flask, React, Next.js, Vue.js, Node.js, Express
- Ma'lumotlar bazasi: PostgreSQL, MongoDB, Redis, MySQL
- DevOps: Docker, Kubernetes, Git, CI/CD
- Frontend: HTML, CSS, Responsive Design, Browser APIs

JAVOB BERISH QOIDALARI:
1. Savollarga IXCHAM, ANIQ va TO'LIQ texnik javob ber
2. Kod misollarini ODDIY MATN formatida yoz (backtick ishlatma)
3. Texnik terminlarni inglizcha qoldiring, tushuntirishni o'zbekcha bering
4. Agar kod xatosi bo'lsa, xatoning sababini tushuntir va to'g'ri kodini ko'rsat
5. Best practice va xavfsizlik masalalarini eslatib o't
6. Rasmiy dokumentatsiya havolalarini tavsiya qil
7. Murakkab mavzularni oddiy tilda tushuntir
8. Agar savol noaniq bo'lsa, aniqlashtiruvchi savol ber
9. Kod misollarida izohlar (comments) qo'sh
10. JAVOBNI QISQA VA ANIQ QILIB BER - ortiqcha so'z ishlatma!
11. ODDIY MATN FORMATIDA YOZ - murakkab jadval yoki markdown ishlatma!

JAVOB FORMATI:
- Oddiy matn (plain text)
- Kod uchun: oddiy matn, har bir qator yangi qatordan
- Ro'yxat: 1., 2., 3. yoki • ishlatgin
- Emoji: ✅ ❌ 💡 📌 🔥

"""
        
        # Add detected context
        if technical_context.primary_language:
            prompt += f"\nDasturlash tili: {technical_context.primary_language.upper()}\n"
        
        if technical_context.framework:
            prompt += f"Framework: {technical_context.framework}\n"
        
        if technical_context.topic:
            prompt += f"Mavzu: {technical_context.topic}\n"
        
        # Add code snippet if present
        if code_snippet:
            prompt += f"\nFOYDALANUVCHI KODI:\n```{code_snippet.language or 'text'}\n{code_snippet.code}\n```\n"
            if code_snippet.has_error:
                prompt += "\n⚠️ Bu kodda xato bor. Xatoni toping va tuzating.\n"
        
        # Add error information if present
        if error_info:
            prompt += f"\nXATO XABARI:\n{error_info.error_type}: {error_info.error_message}\n"
            if error_info.stack_trace:
                prompt += f"\nStack trace:\n{error_info.stack_trace[:500]}\n"  # Limit stack trace length
            prompt += "\n⚠️ Bu xatoning sababini tushuntir va yechimini ko'rsat.\n"
        
        # Add user question
        prompt += f"\nFOYDALANUVCHI SAVOLI:\n{user_question}\n"
        
        # Add response instruction
        prompt += "\nTEXNIK JAVOB (O'zbek tilida, kod misollari bilan):\n"
        
        return prompt
