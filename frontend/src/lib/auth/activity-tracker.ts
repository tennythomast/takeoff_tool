/**
 * User Activity Tracker
 * Tracks user activity and extends token expiry when user is active
 */

// Constants
const INACTIVITY_THRESHOLD = 30 * 60 * 1000; // 30 minutes in milliseconds
const ACTIVITY_CHECK_INTERVAL = 60 * 1000; // Check every minute

// Track the last activity timestamp
let lastActivityTimestamp = Date.now();

// Track if the activity tracker is initialized
let isInitialized = false;

// Events to track for user activity
const activityEvents = [
  'mousedown',
  'mousemove',
  'keypress',
  'scroll',
  'touchstart',
  'click',
  'focus',
];

/**
 * Update the last activity timestamp
 */
function updateActivityTimestamp() {
  lastActivityTimestamp = Date.now();
}

/**
 * Check if the user has been inactive for longer than the threshold
 * @returns {boolean} True if user is considered inactive
 */
export function isUserInactive(): boolean {
  const currentTime = Date.now();
  return currentTime - lastActivityTimestamp > INACTIVITY_THRESHOLD;
}

/**
 * Get the time since last user activity in milliseconds
 * @returns {number} Time in milliseconds since last activity
 */
export function getTimeSinceLastActivity(): number {
  return Date.now() - lastActivityTimestamp;
}

/**
 * Initialize the activity tracker
 * Sets up event listeners for user activity
 */
export function initActivityTracker() {
  if (isInitialized || typeof window === 'undefined') {
    return;
  }
  
  // Set up event listeners for user activity
  activityEvents.forEach(eventType => {
    window.addEventListener(eventType, updateActivityTimestamp, { passive: true });
  });
  
  // Mark as initialized
  isInitialized = true;
  
  // Set initial activity timestamp
  updateActivityTimestamp();
  
  console.log('[ActivityTracker] Initialized');
}

/**
 * Clean up the activity tracker
 * Removes event listeners
 */
export function cleanupActivityTracker() {
  if (!isInitialized || typeof window === 'undefined') {
    return;
  }
  
  // Remove event listeners
  activityEvents.forEach(eventType => {
    window.removeEventListener(eventType, updateActivityTimestamp);
  });
  
  // Mark as not initialized
  isInitialized = false;
  
  console.log('[ActivityTracker] Cleaned up');
}
