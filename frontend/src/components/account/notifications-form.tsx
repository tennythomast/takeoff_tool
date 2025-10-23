"use client"

import { useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm, SubmitHandler } from "react-hook-form"
import * as z from "zod"
import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form"
import { Switch } from "@/components/ui/switch"
import { toast } from "@/components/ui/use-toast"
import { updateNotificationPreferences } from "@/lib/api/user-api"
import { Loader2 } from "lucide-react"

const notificationsFormSchema = z.object({
  aiUsageAlerts: z.boolean().default(false),
  emailNotifications: z.boolean().default(false),
  securityAlerts: z.boolean().default(true),
  productUpdates: z.boolean().default(false),
})

type NotificationsFormValues = z.infer<typeof notificationsFormSchema>

interface NotificationsFormProps {
  user: {
    id: string
    default_org?: string
  }
}

export function NotificationsForm({ user }: NotificationsFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)

  const form = useForm<NotificationsFormValues>({
    resolver: zodResolver(notificationsFormSchema) as any,
    defaultValues: {
      aiUsageAlerts: true,
      emailNotifications: true,
      securityAlerts: true,
      productUpdates: false,
    },
  })

  const onSubmit: SubmitHandler<NotificationsFormValues> = async (data) => {
    setIsSubmitting(true)
    try {
      // Call API to update notification preferences
      await updateNotificationPreferences({
        userId: user.id,
        orgId: user.default_org,
        preferences: {
          ai_usage_alerts: data.aiUsageAlerts,
          email_notifications: data.emailNotifications,
          security_alerts: data.securityAlerts,
          product_updates: data.productUpdates,
        }
      })
      
      toast({
        title: "Preferences updated",
        description: "Your notification preferences have been updated successfully.",
      })
    } catch (error) {
      console.error("Failed to update notification preferences:", error)
      toast({
        title: "Update failed",
        description: "There was a problem updating your notification preferences. Please try again.",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit as any)} className="space-y-6">
        <div className="space-y-4">
          <FormField
            control={form.control as any}
            name="aiUsageAlerts"
            render={({ field }: { field: any }) => (
              <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5">
                  <FormLabel className="text-base">AI Usage Alerts</FormLabel>
                  <FormDescription>
                    Receive notifications when approaching your AI budget limits.
                  </FormDescription>
                </div>
                <FormControl>
                  <Switch
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                </FormControl>
              </FormItem>
            )}
          />
          
          <FormField
            control={form.control as any}
            name="emailNotifications"
            render={({ field }: { field: any }) => (
              <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5">
                  <FormLabel className="text-base">Email Notifications</FormLabel>
                  <FormDescription>
                    Receive email notifications for important updates and alerts.
                  </FormDescription>
                </div>
                <FormControl>
                  <Switch
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                </FormControl>
              </FormItem>
            )}
          />
          
          <FormField
            control={form.control as any}
            name="securityAlerts"
            render={({ field }: { field: any }) => (
              <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5">
                  <FormLabel className="text-base">Security Alerts</FormLabel>
                  <FormDescription>
                    Receive notifications about security-related events such as password changes and login attempts.
                  </FormDescription>
                </div>
                <FormControl>
                  <Switch
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                </FormControl>
              </FormItem>
            )}
          />
          
          <FormField
            control={form.control as any}
            name="productUpdates"
            render={({ field }: { field: any }) => (
              <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5">
                  <FormLabel className="text-base">Product Updates</FormLabel>
                  <FormDescription>
                    Receive updates about new features and improvements to the platform.
                  </FormDescription>
                </div>
                <FormControl>
                  <Switch
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                </FormControl>
              </FormItem>
            )}
          />
        </div>
        
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isSubmitting ? "Saving..." : "Save preferences"}
        </Button>
      </form>
    </Form>
  )
}
