import { API_BASE_URL } from "@/lib/config"
import { getAuthHeaders } from "@/lib/auth/auth-api"

/**
 * Update user profile information
 * Email is now optional as it's not editable in the UI
 */
export async function updateUserProfile(userData: {
  first_name: string
  last_name: string
  email?: string
}) {
  const response = await fetch(`${API_BASE_URL}/api/v1/users/me/`, {
    method: "PATCH",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      first_name: userData.first_name,
      last_name: userData.last_name,
      email: userData.email,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || "Failed to update user profile")
  }

  return await response.json()
}

/**
 * Change user password
 */
export async function changePassword(passwordData: {
  current_password: string
  new_password: string
}) {
  const response = await fetch(`${API_BASE_URL}/api/v1/users/change-password/`, {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(passwordData),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || "Failed to change password")
  }

  return await response.json()
}

/**
 * Update user notification preferences
 */
export async function updateNotificationPreferences(data: {
  userId: string
  orgId?: string
  preferences: {
    ai_usage_alerts: boolean
    email_notifications: boolean
    security_alerts: boolean
    product_updates: boolean
  }
}) {
  // If we have an organization ID, update org-level preferences
  if (data.orgId) {
    const response = await fetch(`${API_BASE_URL}/api/v1/organizations/${data.orgId}/`, {
      method: "PATCH",
      headers: {
        ...getAuthHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ai_usage_alerts: data.preferences.ai_usage_alerts,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || "Failed to update organization notification preferences")
    }
  }

  // Update user-level preferences
  const response = await fetch(`${API_BASE_URL}/api/v1/users/${data.userId}/preferences/`, {
    method: "PATCH",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email_notifications: data.preferences.email_notifications,
      security_alerts: data.preferences.security_alerts,
      product_updates: data.preferences.product_updates,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || "Failed to update user notification preferences")
  }

  return await response.json()
}
