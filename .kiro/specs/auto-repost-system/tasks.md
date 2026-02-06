# Implementation Plan: Auto Repost System

## Overview

This implementation plan breaks down the auto-repost system into discrete coding tasks. The approach follows an incremental pattern: first establish the data models and database layer, then build the core reposting service, add the monitoring scheduler, integrate admin commands, and finally add comprehensive testing.

Each task builds on previous work, with checkpoints to ensure stability before proceeding. Testing tasks are marked as optional (*) to allow for faster MVP delivery if needed.

## Tasks

- [x] 1. Create database models for auto-repost system
  - [x] 1.1 Create RepostConfig model
    - Define SQLAlchemy model with all fields (source_channel_id, target_channel_id, settings, filters, etc.)
    - Add relationships and constraints
    - Include TimestampMixin for created_at/updated_at
    - _Requirements: 1.1, 4.1, 4.2, 4.3, 4.4, 9.1_
  
  - [x] 1.2 Create RepostLog model
    - Define model for logging individual repost operations
    - Include foreign key to RepostConfig with cascade delete
    - Add fields for status tracking and error messages
    - _Requirements: 9.4, 9.5_
  
  - [x] 1.3 Create RepostStats model
    - Define model for aggregated statistics
    - Include counters for successful/failed/filtered reposts
    - Add JSON field for content type breakdown
    - Include foreign key to RepostConfig with cascade delete
    - _Requirements: 7.1, 7.3, 9.4, 9.5_
  
  - [x] 1.4 Update models __init__.py to export new models
    - Add imports for RepostConfig, RepostLog, RepostStats
    - Update __all__ list
    - _Requirements: 10.4_
  
  - [ ]* 1.5 Write property test for referential integrity
    - **Property 19: Referential Integrity**
    - Test that deleting a config cascades to logs and stats
    - **Validates: Requirements 9.5**

- [-] 2. Create database migration for new tables
  - [x] 2.1 Generate Alembic migration script
    - Run alembic revision --autogenerate
    - Review generated migration for correctness
    - Add any custom constraints or indexes
    - _Requirements: 9.1, 9.2_
  
  - [x] 2.2 Test migration up and down
    - Apply migration to test database
    - Verify tables created correctly
    - Test rollback functionality
    - _Requirements: 9.1_

- [-] 3. Implement core AutoRepostService
  - [x] 3.1 Create AutoRepostService class skeleton
    - Create src/services/auto_repost_service.py
    - Define __init__ with bot and session parameters
    - Add placeholder methods for core functionality
    - _Requirements: 2.1, 3.1_
  
  - [x] 3.2 Implement get_new_messages method
    - Fetch messages from source channel using Telegram API
    - Filter by message_id > last_processed_message_id
    - Handle pagination for large message batches
    - Handle API errors gracefully
    - _Requirements: 2.2, 2.3, 8.3_
  
  - [x] 3.3 Implement apply_content_filter method
    - Determine message content type (text, photo, video, etc.)
    - Check against allowed_content_types list
    - Return True if allowed or no filter configured
    - Handle messages with multiple media attachments
    - _Requirements: 4.4, 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [ ]* 3.4 Write property test for content type filtering
    - **Property 10: Content Type Filtering**
    - **Property 11: Default Filter Behavior**
    - Test filtering logic with various content types
    - **Validates: Requirements 4.4, 5.1, 5.2, 5.4**
  
  - [x] 3.5 Implement copy_message_with_watermark method
    - Handle different message types (text, photo, video, document, etc.)
    - Append watermark to caption or text if configured
    - Use bot.copy_message or manual copying based on remove_forward_attribution
    - Preserve media and formatting
    - _Requirements: 3.2, 3.5, 3.6, 4.2_
  
  - [ ]* 3.6 Write property test for watermark application
    - **Property 8: Watermark Application**
    - Test that watermarks are correctly appended
    - **Validates: Requirements 3.2, 4.2**
  
  - [ ]* 3.7 Write property test for content type preservation
    - **Property 7: Content Type Preservation**
    - Test that reposted messages maintain original content type
    - **Validates: Requirements 3.5**
  
  - [ ]* 3.8 Write property test for forward attribution control
    - **Property 9: Forward Attribution Control**
    - Test copy vs forward behavior based on configuration
    - **Validates: Requirements 3.6, 4.6**

- [-] 4. Implement repost operation and error handling
  - [x] 4.1 Implement repost_message method
    - Apply content filter
    - Call copy_message_with_watermark if filter passes
    - Apply repost delay if configured
    - Handle errors with retry logic (up to 3 attempts with exponential backoff)
    - Log result to RepostLog
    - Update statistics
    - _Requirements: 3.1, 3.3, 3.4, 8.3_
  
  - [x] 4.2 Implement update_statistics method
    - Increment appropriate counters (successful/failed/filtered)
    - Update content_type_counts JSON field
    - Update last_repost_at timestamp
    - Commit changes to database
    - _Requirements: 7.1, 7.3, 7.4_
  
  - [ ]* 4.3 Write property test for statistics accuracy
    - **Property 15: Statistics Accuracy**
    - Test that counters accurately reflect operations
    - **Validates: Requirements 7.1, 7.3, 7.4**
  
  - [ ] 4.4 Implement error handling and status updates
    - Update config status to "error" on channel access failures
    - Store error message in last_error field
    - Send admin notification on persistent errors
    - _Requirements: 8.1, 8.2, 8.4_
  
  - [ ]* 4.5 Write property test for error status updates
    - **Property 17: Error Status Updates**
    - Test that errors update channel status correctly
    - **Validates: Requirements 8.1**

- [-] 5. Implement monitoring logic
  - [x] 5.1 Implement monitor_source method
    - Get new messages using get_new_messages
    - For each message, call repost_message
    - Update last_processed_message_id after processing
    - Update last_check_at timestamp
    - Handle errors without stopping other channels
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [ ]* 5.2 Write property test for no duplicate processing
    - **Property 4: No Duplicate Processing**
    - Test that last_processed_message_id prevents duplicates
    - **Validates: Requirements 2.3**
  
  - [ ]* 5.3 Write property test for new message detection
    - **Property 6: New Message Detection**
    - Test that new messages are identified correctly
    - **Validates: Requirements 2.2**
  
  - [x] 5.4 Implement monitor_all_sources method
    - Query all enabled RepostConfig records
    - For each config, call monitor_source
    - Implement error isolation (continue on individual failures)
    - Log overall monitoring cycle completion
    - _Requirements: 2.1, 2.4, 8.5_
  
  - [ ]* 5.5 Write property test for error isolation
    - **Property 5: Error Isolation**
    - Test that one channel failure doesn't stop others
    - **Validates: Requirements 2.4, 8.5**

- [ ] 6. Checkpoint - Test core reposting functionality
  - Ensure all tests pass
  - Manually test reposting a message from one channel to another
  - Verify database records are created correctly
  - Ask the user if questions arise

- [-] 7. Implement background scheduler
  - [x] 7.1 Create background task runner
    - Create src/services/repost_scheduler.py
    - Implement asyncio-based scheduler that runs monitor_all_sources periodically
    - Use configurable interval (default 120 seconds)
    - Handle graceful shutdown
    - _Requirements: 2.1, 2.5_
  
  - [x] 7.2 Integrate scheduler with bot lifecycle
    - Start scheduler when bot starts
    - Stop scheduler when bot stops
    - Add to main.py or bot initialization
    - _Requirements: 2.5_
  
  - [x] 7.3 Add scheduler health monitoring
    - Log scheduler start/stop events
    - Track last execution time
    - Alert on scheduler failures
    - _Requirements: 2.5_

- [-] 8. Implement admin commands for channel management
  - [x] 8.1 Implement /autorepost add command
    - Parse channel identifier (username or ID)
    - Validate bot has access to source channel
    - Prompt for target channel
    - Create RepostConfig with default settings
    - Create initial RepostStats record
    - Send confirmation message
    - _Requirements: 1.1, 1.2, 1.5, 4.1_
  
  - [ ]* 8.2 Write property test for channel addition
    - **Property 1: Channel Addition and Persistence**
    - Test that added channels persist and appear in list
    - **Validates: Requirements 1.1, 1.4, 9.1, 9.3**
  
  - [ ]* 8.3 Write property test for invalid channel rejection
    - **Property 2: Invalid Channel Rejection**
    - Test that invalid channels are rejected
    - **Validates: Requirements 1.2, 1.5**
  
  - [x] 8.2 Implement /autorepost list command
    - Query all RepostConfig records
    - Display formatted list with status, source, target
    - Show enabled/disabled status
    - Include basic stats (total reposts)
    - _Requirements: 1.4, 6.4_
  
  - [x] 8.3 Implement /autorepost remove command
    - Parse source channel identifier
    - Delete RepostConfig (cascade deletes logs/stats)
    - Send confirmation message
    - _Requirements: 1.3_
  
  - [ ]* 8.4 Write property test for channel removal
    - **Property 3: Channel Removal Preserves History**
    - Test that removal deletes config but preserves logs
    - **Validates: Requirements 1.3**

- [ ] 9. Implement admin commands for configuration
  - [ ] 9.1 Implement /autorepost config command
    - Show inline keyboard with configuration options
    - Options: target channel, watermark, filters, delay, attribution
    - Handle callback queries for each option
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.6_
  
  - [ ] 9.2 Implement watermark configuration
    - Prompt for watermark text
    - Validate and store in RepostConfig
    - Send confirmation
    - _Requirements: 4.2_
  
  - [ ] 9.3 Implement content filter configuration
    - Show checkboxes for content types
    - Store selected types in allowed_content_types
    - Handle empty selection (allow all)
    - _Requirements: 4.4, 5.3_
  
  - [ ] 9.4 Implement delay configuration
    - Prompt for delay in seconds
    - Validate range (1-3600)
    - Store in repost_delay_seconds
    - _Requirements: 4.3_
  
  - [ ]* 9.5 Write property test for delay validation
    - **Property 12: Delay Validation**
    - Test that invalid delays are rejected
    - **Validates: Requirements 4.3**
  
  - [ ] 9.6 Implement forward attribution toggle
    - Toggle remove_forward_attribution boolean
    - Send confirmation with current setting
    - _Requirements: 4.6_
  
  - [ ]* 9.7 Write property test for independent configuration
    - **Property 13: Independent Configuration**
    - Test that configs don't interfere with each other
    - **Validates: Requirements 4.5**
  
  - [ ]* 9.8 Write property test for configuration atomicity
    - **Property 18: Configuration Atomicity**
    - Test that updates are atomic (all or nothing)
    - **Validates: Requirements 9.2**

- [ ] 10. Implement enable/disable commands
  - [x] 10.1 Implement /autorepost enable command
    - Parse source channel identifier
    - Set is_enabled = True
    - Send confirmation
    - _Requirements: 6.2_
  
  - [x] 10.2 Implement /autorepost disable command
    - Parse source channel identifier
    - Set is_enabled = False
    - Send confirmation
    - _Requirements: 6.1_
  
  - [ ]* 10.3 Write property test for enable/disable state preservation
    - **Property 14: Enable/Disable State Preservation**
    - Test that disable/enable preserves configuration
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

- [ ] 11. Implement statistics commands
  - [x] 11.1 Implement /autorepost stats command
    - Query RepostStats for all or specific channel
    - Display formatted statistics
    - Include time range information
    - Show breakdown by content type
    - _Requirements: 7.1, 7.2, 7.3, 7.5_
  
  - [ ]* 11.2 Write property test for statistics filtering
    - **Property 16: Statistics Filtering**
    - Test that stats are correctly filtered by channel
    - **Validates: Requirements 7.5**

- [ ] 12. Add admin authorization checks
  - [ ] 12.1 Add permission checks to all autorepost commands
    - Verify user_id in config.ADMIN_USER_IDS
    - Return error message for non-admins
    - Apply to all /autorepost subcommands
    - _Requirements: 10.2_
  
  - [ ]* 12.2 Write property test for admin authorization
    - **Property 20: Admin Authorization**
    - Test that non-admins are rejected
    - **Validates: Requirements 10.2**

- [x] 13. Update services __init__.py
  - Add AutoRepostService to exports
  - Add RepostScheduler to exports
  - Update __all__ list
  - _Requirements: 10.4_

- [ ] 14. Checkpoint - Test complete system
  - Ensure all tests pass
  - Test end-to-end flow: add channel, configure, monitor, repost
  - Verify statistics are tracked correctly
  - Test error handling with inaccessible channels
  - Ask the user if questions arise

- [ ] 15. Add integration tests
  - [ ]* 15.1 Write integration test for complete repost flow
    - Test adding channel, configuring, and reposting
    - Verify database state at each step
    - Test with different content types
    - _Requirements: All_
  
  - [ ]* 15.2 Write integration test for error recovery
    - Test handling of inaccessible channels
    - Test retry logic
    - Test error notifications
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  
  - [ ]* 15.3 Write integration test for statistics tracking
    - Perform multiple reposts
    - Verify statistics accuracy
    - Test filtering by channel
    - _Requirements: 7.1, 7.3, 7.4, 7.5_

- [ ] 16. Add documentation
  - [ ] 16.1 Add docstrings to all public methods
    - Document parameters and return types
    - Include usage examples
    - Document error conditions
    - _Requirements: 10.3_
  
  - [ ] 16.2 Create user guide for admin commands
    - Document all /autorepost commands
    - Include examples and screenshots
    - Explain configuration options
    - _Requirements: 10.3_

- [ ] 17. Final checkpoint - Production readiness
  - Run full test suite
  - Verify all properties pass with 100+ iterations
  - Test with real Telegram channels (if available)
  - Review error handling and logging
  - Ask the user if ready for deployment

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end flows
- Checkpoints ensure incremental validation before proceeding
