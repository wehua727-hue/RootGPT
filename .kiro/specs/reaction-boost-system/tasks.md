# Implementation Plan: Reaction Boost System

## Overview

This implementation plan adds a reaction boost feature to the existing Telegram bot. The bot will support dual operational modes: comment response mode (existing) and reaction boost mode (new). Channels can be configured for either mode or both simultaneously. The implementation focuses on database schema updates, new service components for reaction boosting, admin panel extensions, and comprehensive error handling.

## Tasks

- [ ] 1. Database schema updates and migrations
  - [x] 1.1 Create Alembic migration for Channel model updates
    - Add `mode` column (string, default 'comment')
    - Add `reaction_settings` column (JSON, nullable)
    - Update existing channels to have mode='comment' for backward compatibility
    - _Requirements: 5.1, 5.2, 8.1, 8.2_
  
  - [x] 1.2 Create BoostedPost model and table
    - Define BoostedPost model with channel_id, post_id, boost_timestamp, reaction_count, emojis_used fields
    - Create unique index on (channel_id, post_id)
    - _Requirements: 5.3, 5.4, 5.6_
  
  - [x] 1.3 Create ActivityLog model and table
    - Define ActivityLog model with channel_id, post_id, activity_type, details, timestamp fields
    - Create index on (channel_id, timestamp)
    - _Requirements: 6.1, 6.2, 6.3_
  
  - [ ]* 1.4 Write unit tests for database models
    - Test model creation and relationships
    - Test unique constraints and indexes
    - Test JSON field serialization/deserialization
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 2. Implement ReactionSettings data class and validation
  - [x] 2.1 Create ReactionSettings dataclass
    - Define fields: emojis, reaction_count, delay_min, delay_max, auto_boost
    - Implement validate() method with all validation rules
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_
  
  - [ ]* 2.2 Write property test for ReactionSettings validation
    - **Property 1: Valid settings pass validation**
    - *For any* ReactionSettings with valid values (1-100 reactions, positive delays, non-empty emojis), validation should return (True, None)
    - **Validates: Requirements 2.6, 2.7, 2.8**
  
  - [ ]* 2.3 Write unit tests for ReactionSettings edge cases
    - Test empty emoji list rejection
    - Test reaction count boundaries (0, 1, 100, 101)
    - Test negative delays
    - Test reaction_count > len(emojis)
    - _Requirements: 2.6, 2.7, 2.8_

- [ ] 3. Implement ActivityLogger service
  - [x] 3.1 Create ActivityLogger class
    - Implement log_reaction_added() method
    - Implement log_boost_completed() method
    - Implement log_error() method
    - _Requirements: 6.1, 6.2, 6.3_
  
  - [ ]* 3.2 Write property test for activity logging
    - **Property 2: All logged activities are persisted**
    - *For any* valid activity log entry, after logging it should be retrievable from the database
    - **Validates: Requirements 6.1, 6.2, 6.3**

- [ ] 4. Implement ReactionBoostService
  - [x] 4.1 Create ReactionBoostService class skeleton
    - Initialize with bot, db_session, and logger
    - Define max_retries constant
    - _Requirements: 3.1, 3.2_
  
  - [x] 4.2 Implement _is_already_boosted() method
    - Query BoostedPost table for existing records
    - Return boolean indicating if post was already boosted
    - _Requirements: 3.6_
  
  - [x] 4.3 Implement _select_random_emojis() method
    - Shuffle emoji list for randomization
    - Select configured number of emojis
    - _Requirements: 3.7_
  
  - [ ]* 4.4 Write property test for emoji randomization
    - **Property 3: Emoji selection produces natural variation**
    - *For any* list of emojis and reaction count, multiple calls to _select_random_emojis should produce different orderings
    - **Validates: Requirements 3.7**
  
  - [x] 4.5 Implement _add_reaction_with_retry() method
    - Call Telegram API set_message_reaction
    - Implement exponential backoff retry logic
    - Handle FloodWait exceptions
    - _Requirements: 3.4, 4.1_
  
  - [x] 4.6 Implement _mark_as_boosted() method
    - Create BoostedPost record
    - Store channel_id, post_id, timestamp, reaction_count, emojis_used
    - Commit to database
    - _Requirements: 3.5_
  
  - [x] 4.7 Implement _handle_api_error() method
    - Handle ChatAdminRequired errors (log and disable mode)
    - Handle FloodWait errors (log retry_after)
    - Handle unknown errors (log details)
    - _Requirements: 4.2, 4.3, 4.4, 4.5_
  
  - [x] 4.8 Implement main boost_post() method
    - Check if already boosted (early return)
    - Parse and validate reaction settings
    - Loop through selected emojis
    - Add reactions with delays
    - Log each reaction and completion
    - Mark post as boosted
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_
  
  - [ ]* 4.9 Write property test for boost deduplication
    - **Property 4: Posts are never boosted twice**
    - *For any* post that has been boosted, subsequent boost attempts should be skipped
    - **Validates: Requirements 3.6**
  
  - [ ]* 4.10 Write unit tests for error handling scenarios
    - Test ChatAdminRequired error disables reaction mode
    - Test FloodWait retry logic
    - Test max retry limit
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement PostMonitorService
  - [x] 6.1 Create PostMonitorService class
    - Initialize with bot, db_session, and service references
    - Initialize last_checked dictionary for tracking
    - _Requirements: 3.1_
  
  - [x] 6.2 Implement _get_active_channels() method
    - Query database for active channels
    - Filter by mode field appropriately
    - _Requirements: 5.5_
  
  - [x] 6.3 Implement _fetch_new_posts() method
    - Call Telegram API to get channel messages
    - Filter messages newer than last_checked
    - Update last_checked for channel
    - _Requirements: 3.1_
  
  - [x] 6.4 Implement monitor_channels() main loop
    - Fetch active channels
    - For each channel, fetch new posts
    - Route to reaction service if 'reaction' in mode
    - Route to comment service if 'comment' in mode
    - Handle exceptions and log errors
    - _Requirements: 1.4, 1.5, 3.1_
  
  - [ ]* 6.5 Write property test for mode routing
    - **Property 5: Channel mode determines service routing**
    - *For any* channel with reaction mode enabled, new posts should be routed to ReactionBoostService
    - **Validates: Requirements 1.4, 1.5**
  
  - [ ]* 6.6 Write unit tests for post detection
    - Test new post detection within 60 seconds
    - Test last_checked tracking
    - Test handling of channels with no new posts
    - _Requirements: 3.1_

- [ ] 7. Extend AdminHandler for channel mode configuration
  - [~] 7.1 Implement create_channel_config() method
    - Display mode selection keyboard (comment/reaction/both)
    - Handle callback data for mode selection
    - Store selected mode in database
    - _Requirements: 1.1, 1.2_
  
  - [~] 7.2 Implement configure_reaction_settings() conversation handler
    - Step 1: Collect emoji list from admin
    - Step 2: Collect reaction count (validate 1-100)
    - Step 3: Collect delay range (validate positive numbers)
    - Step 4: Collect auto-boost toggle
    - Validate settings using ReactionSettings.validate()
    - Store settings in channel.reaction_settings
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_
  
  - [~] 7.3 Implement validate_bot_permissions() method
    - Call get_chat_member API for bot user
    - Check if bot is admin or creator
    - Return permission status dictionary
    - _Requirements: 7.1, 7.2, 7.3_
  
  - [~] 7.4 Add permission validation to mode enablement
    - When admin enables Reaction_Boost_Mode, call validate_bot_permissions()
    - Display warning if bot is not admin
    - Show instructions for granting permissions
    - _Requirements: 7.1, 7.2_
  
  - [~] 7.5 Implement display_activity_logs() method
    - Query ActivityLog table for channel
    - Order by timestamp descending
    - Limit to recent 50 entries
    - Format logs for display
    - _Requirements: 6.4_
  
  - [~] 7.6 Add error count display to admin panel
    - Query ActivityLog for error entries
    - Display error count and last error timestamp per channel
    - _Requirements: 6.5_
  
  - [ ]* 7.7 Write unit tests for admin panel handlers
    - Test mode selection flow
    - Test reaction settings validation
    - Test permission checking
    - Test activity log display
    - _Requirements: 1.1, 1.2, 2.1, 7.1, 6.4_

- [ ] 8. Implement permission monitoring and auto-disable
  - [~] 8.1 Add periodic permission check to PostMonitorService
    - Check bot permissions before boosting
    - If ChatAdminRequired error occurs, disable reaction mode
    - Log warning when permissions are lost
    - _Requirements: 3.8, 7.4_
  
  - [~] 8.2 Implement re-enable functionality in admin panel
    - Add "Re-check Permissions" button for each channel
    - Call validate_bot_permissions() on click
    - Re-enable Reaction_Boost_Mode if permissions are valid
    - _Requirements: 7.5_
  
  - [ ]* 8.3 Write unit tests for permission monitoring
    - Test auto-disable on permission loss
    - Test re-enable after permission restoration
    - _Requirements: 7.4, 7.5_

- [ ] 9. Integration and backward compatibility
  - [~] 9.1 Update main bot initialization
    - Initialize ReactionBoostService
    - Initialize PostMonitorService with both services
    - Start monitoring loop
    - _Requirements: 1.4, 1.5_
  
  - [~] 9.2 Verify backward compatibility
    - Test that existing channels continue working
    - Verify default mode='comment' for migrated channels
    - Test that comment response functionality is unaffected
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  
  - [ ]* 9.3 Write integration tests for dual-mode operation
    - Test channel with both modes enabled
    - Verify both services are invoked for new posts
    - Test mode switching (comment -> reaction -> both)
    - _Requirements: 1.1, 1.4, 1.5_

- [ ] 10. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The implementation uses Python with async/await and SQLAlchemy
- Property tests should run minimum 100 iterations
- Checkpoints ensure incremental validation
- The design maintains backward compatibility with existing comment response functionality
