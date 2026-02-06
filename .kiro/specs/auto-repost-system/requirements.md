# Requirements Document: Auto Repost System

## Introduction

The Auto Repost System enables Telegram bot administrators to automatically monitor and repost content from source channels to target channels. This feature provides flexible configuration options for content filtering, scheduling, and monitoring to ensure efficient content distribution while maintaining control over what gets reposted.

## Glossary

- **Admin**: A user with administrative privileges who can configure the auto-repost system
- **Source_Channel**: A Telegram channel that the bot monitors for new content
- **Target_Channel**: A Telegram channel where the bot reposts content from source channels
- **Repost**: The action of forwarding or copying a message from a source channel to a target channel
- **Monitor_Service**: The background service that checks source channels for new posts
- **Repost_Config**: Configuration settings that control how content is reposted from a specific source channel
- **Content_Filter**: Rules that determine which types of content should be reposted
- **Watermark**: Optional text or caption added to reposted content
- **Repost_Statistics**: Data tracking the number and source of reposted messages

## Requirements

### Requirement 1: Source Channel Management

**User Story:** As an admin, I want to add and manage source channels to monitor, so that I can control which channels the bot watches for content.

#### Acceptance Criteria

1. WHEN an admin provides a valid channel username or ID, THE System SHALL add the channel to the monitored sources list
2. WHEN an admin provides an invalid channel identifier, THE System SHALL return a descriptive error message
3. WHEN an admin requests to remove a source channel, THE System SHALL remove it from monitoring and preserve historical repost data
4. WHEN an admin requests the list of source channels, THE System SHALL display all configured source channels with their current status
5. THE System SHALL validate that the bot has access to read messages from the source channel before adding it

### Requirement 2: Content Monitoring

**User Story:** As an admin, I want the bot to automatically check source channels for new posts, so that content can be reposted without manual intervention.

#### Acceptance Criteria

1. THE Monitor_Service SHALL check each enabled source channel for new posts at configurable intervals (default 2 minutes)
2. WHEN a new post is detected in a source channel, THE Monitor_Service SHALL identify it as a candidate for reposting
3. WHEN checking for new posts, THE Monitor_Service SHALL track the last processed message ID to avoid duplicate processing
4. IF the Monitor_Service cannot access a source channel, THEN THE System SHALL log the error and continue monitoring other channels
5. THE Monitor_Service SHALL operate continuously without requiring manual restarts
6. WHERE configured to start from oldest, THE Monitor_Service SHALL begin processing from the earliest available message in the channel

### Requirement 3: Content Reposting

**User Story:** As an admin, I want detected posts to be automatically reposted to my target channel, so that my audience receives timely content updates.

#### Acceptance Criteria

1. WHEN a new post is detected and passes all filters, THE System SHALL repost it to the configured target channel
2. WHERE a watermark is configured, THE System SHALL append the watermark text to the reposted content
3. WHERE a repost delay is configured, THE System SHALL wait the specified duration before reposting the next message
4. WHEN reposting fails due to permissions or network errors, THE System SHALL log the error and retry up to 3 times with exponential backoff
5. THE System SHALL preserve the original media type when reposting (photo, video, document, text)
6. WHERE configured to remove forward attribution, THE System SHALL copy the content without the "Forwarded from" header

### Requirement 4: Repost Configuration

**User Story:** As an admin, I want to configure repost behavior for each source channel, so that I can customize how content is handled.

#### Acceptance Criteria

1. WHEN an admin configures a target channel for a source, THE System SHALL validate that the bot has permission to post in the target channel
2. WHEN an admin sets a watermark, THE System SHALL store it and apply it to all future reposts from that source
3. WHEN an admin sets a repost delay, THE System SHALL enforce a minimum delay of 1 second and maximum delay of 3600 seconds
4. WHERE content type filters are configured, THE System SHALL only repost messages matching the specified types
5. THE System SHALL allow independent configuration for each source channel
6. WHEN an admin configures to remove forward attribution, THE System SHALL copy content instead of forwarding it

### Requirement 5: Content Filtering

**User Story:** As an admin, I want to filter which types of content get reposted, so that only relevant content reaches my target channel.

#### Acceptance Criteria

1. WHEN a content type filter is active, THE Content_Filter SHALL evaluate each new post against the filter criteria
2. WHERE multiple content types are allowed, THE Content_Filter SHALL repost messages containing any of the allowed types
3. THE System SHALL support filtering by text, photo, video, document, audio, and animation content types
4. WHEN no content type filter is configured, THE System SHALL repost all content types
5. THE Content_Filter SHALL correctly identify content types for messages with multiple media attachments

### Requirement 6: Enable/Disable Control

**User Story:** As an admin, I want to enable or disable auto-repost for individual source channels, so that I can temporarily pause monitoring without losing configuration.

#### Acceptance Criteria

1. WHEN an admin disables a source channel, THE Monitor_Service SHALL stop checking that channel for new posts
2. WHEN an admin enables a previously disabled source channel, THE Monitor_Service SHALL resume checking for new posts
3. WHILE a source channel is disabled, THE System SHALL preserve all configuration settings
4. THE System SHALL display the enabled/disabled status for each source channel in the channel list
5. WHEN a source channel is disabled, THE System SHALL complete any in-progress repost operations before stopping

### Requirement 7: Repost Statistics

**User Story:** As an admin, I want to view statistics about reposted content, so that I can understand which sources are most active and monitor system performance.

#### Acceptance Criteria

1. WHEN an admin requests statistics, THE System SHALL display the total number of posts reposted from each source channel
2. WHEN an admin requests statistics, THE System SHALL display the time range of the statistics
3. THE System SHALL track successful reposts, failed reposts, and filtered posts separately
4. THE Repost_Statistics SHALL update immediately after each repost operation
5. WHEN an admin requests statistics for a specific source channel, THE System SHALL display detailed metrics for only that channel

### Requirement 8: Error Handling

**User Story:** As an admin, I want the system to handle errors gracefully, so that temporary issues don't break the entire auto-repost functionality.

#### Acceptance Criteria

1. IF a source channel becomes inaccessible, THEN THE System SHALL log the error and mark the channel status as "error"
2. IF the target channel becomes inaccessible, THEN THE System SHALL log the error and pause reposting until access is restored
3. WHEN a network error occurs during monitoring, THE System SHALL retry the operation after a brief delay
4. WHEN an error occurs, THE System SHALL send a notification to the admin with error details
5. THE System SHALL continue monitoring other source channels even when one channel encounters errors

### Requirement 9: Database Persistence

**User Story:** As a system administrator, I want all configuration and statistics to be persisted in the database, so that settings survive bot restarts.

#### Acceptance Criteria

1. WHEN a source channel is added, THE System SHALL store its configuration in the database immediately
2. WHEN configuration is updated, THE System SHALL update the database record atomically
3. WHEN the bot restarts, THE System SHALL load all source channel configurations from the database
4. THE System SHALL store repost statistics with timestamps for historical tracking
5. THE System SHALL maintain referential integrity between source channels, target channels, and repost records

### Requirement 10: Admin Interface Integration

**User Story:** As an admin, I want to manage auto-repost settings through the existing admin interface, so that I have a consistent user experience.

#### Acceptance Criteria

1. THE System SHALL provide admin commands that follow the existing command pattern in the bot
2. WHEN an admin uses auto-repost commands, THE System SHALL verify admin permissions before executing
3. THE System SHALL provide clear feedback messages for all admin actions
4. THE System SHALL integrate with the existing admin handler structure
5. THE System SHALL use the existing database session management patterns
