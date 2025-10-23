"use client"

import { useState, useEffect } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import * as z from "zod"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "@/components/ui/use-toast"
import { fetchOrganizationDetails, updateOrganization } from "@/lib/api/organization-api"
import { Loader2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"

const organizationFormSchema = z.object({
  name: z.string().min(2, {
    message: "Organization name must be at least 2 characters.",
  }),
  apiKeyStrategy: z.enum(["DATAELAN", "BYOK", "HYBRID"], {
    required_error: "Please select an API key strategy.",
  }),
  monthlyAiBudget: z.string().refine((val) => !val || !isNaN(parseFloat(val)), {
    message: "Budget must be a valid number.",
  }),
  defaultOptimizationStrategy: z.enum(["cost_first", "balanced", "performance_first"], {
    required_error: "Please select an optimization strategy.",
  }),
})

type OrganizationFormValues = z.infer<typeof organizationFormSchema>

interface OrganizationSettingsProps {
  user: {
    id: string
    default_org?: string
  }
}

export function OrganizationSettings({ user }: OrganizationSettingsProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [organization, setOrganization] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const form = useForm<OrganizationFormValues>({
    resolver: zodResolver(organizationFormSchema),
    defaultValues: {
      name: "",
      apiKeyStrategy: "DATAELAN",
      monthlyAiBudget: "",
      defaultOptimizationStrategy: "balanced",
    },
  })

  useEffect(() => {
    const fetchOrgData = async () => {
      try {
        setLoading(true)
        // Fetch organization data from API
        const orgData = await fetchOrganizationDetails(user.default_org)
        setOrganization(orgData)
        
        // Set form default values
        form.reset({
          name: orgData.name,
          apiKeyStrategy: orgData.api_key_strategy,
          monthlyAiBudget: orgData.monthly_ai_budget ? orgData.monthly_ai_budget.toString() : "",
          defaultOptimizationStrategy: orgData.default_optimization_strategy,
        })
      } catch (err) {
        console.error("Error fetching organization data:", err)
        setError("Failed to load organization data. Please try again.")
      } finally {
        setLoading(false)
      }
    }

    if (user.default_org) {
      fetchOrgData()
    } else {
      setLoading(false)
      setError("No default organization found for this user.")
    }
  }, [user.default_org, form])

  async function onSubmit(data: OrganizationFormValues) {
    if (!organization) return

    setIsSubmitting(true)
    try {
      // Call API to update organization
      const updatedOrg = await updateOrganization({
        id: organization.id,
        name: data.name,
        api_key_strategy: data.apiKeyStrategy,
        monthly_ai_budget: data.monthlyAiBudget ? parseFloat(data.monthlyAiBudget) : null,
        default_optimization_strategy: data.defaultOptimizationStrategy,
      })
      
      // Update the organization state with new data
      setOrganization(updatedOrg)
      
      toast({
        title: "Organization updated",
        description: "Your organization settings have been updated successfully.",
      })
    } catch (error) {
      console.error("Failed to update organization:", error)
      toast({
        title: "Update failed",
        description: "There was a problem updating your organization settings. Please try again.",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-[200px] w-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2">Loading organization information...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-md bg-destructive/15 p-4 text-destructive">
        <p>{error}</p>
      </div>
    )
  }

  if (!organization) {
    return (
      <div className="rounded-md bg-muted p-4">
        <p>No organization information available.</p>
      </div>
    )
  }

  // Calculate budget usage percentage
  const budgetPercentage = organization.budget_status?.percentage || 0
  const budgetStatus = organization.budget_status?.status || "normal"

  return (
    <div className="space-y-8">
      {/* Budget Overview Card */}
      <Card>
        <CardHeader>
          <CardTitle>Budget Overview</CardTitle>
        </CardHeader>
        <CardContent>
          {organization.budget_status?.has_budget ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Monthly AI Budget</span>
                <span className="font-bold">${organization.budget_status.budget.toFixed(2)}</span>
              </div>
              
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>Current Spend: ${organization.budget_status.current_spend.toFixed(2)}</span>
                  <span>Remaining: ${organization.budget_status.remaining.toFixed(2)}</span>
                </div>
                <Progress 
                  value={budgetPercentage} 
                  className={`h-2 ${
                    budgetStatus === "critical" ? "bg-red-100" : 
                    budgetStatus === "warning" ? "bg-amber-100" : "bg-blue-100"
                  } [&>div]:${
                    budgetStatus === "critical" ? "bg-red-500" : 
                    budgetStatus === "warning" ? "bg-amber-500" : "bg-blue-500"
                  }`}
                />
                <p className={`text-xs ${
                  budgetStatus === "critical" ? "text-red-500" : 
                  budgetStatus === "warning" ? "text-amber-500" : "text-blue-500"
                }`}>
                  {budgetPercentage.toFixed(1)}% of budget used
                </p>
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground">No budget has been set for this organization.</p>
          )}
        </CardContent>
      </Card>

      {/* Organization Settings Form */}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Organization Name</FormLabel>
                <FormControl>
                  <Input placeholder="Acme Inc." {...field} className="bg-white" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          
          <FormField
            control={form.control}
            name="apiKeyStrategy"
            render={({ field }) => (
              <FormItem>
                <FormLabel>API Key Strategy</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl>
                    <SelectTrigger className="bg-white">
                      <SelectValue placeholder="Select API key strategy" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="DATAELAN">Use Dataelan API Keys</SelectItem>
                    <SelectItem value="BYOK">Bring Your Own Keys (BYOK)</SelectItem>
                    <SelectItem value="HYBRID">Mixed Strategy</SelectItem>
                  </SelectContent>
                </Select>
                <FormDescription>
                  Choose how API keys are managed across LLM providers.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
          
          <FormField
            control={form.control}
            name="monthlyAiBudget"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Monthly AI Budget (USD)</FormLabel>
                <FormControl>
                  <Input 
                    type="number"
                    placeholder="500.00" 
                    {...field} 
                    className="bg-white"
                  />
                </FormControl>
                <FormDescription>
                  Set a monthly budget limit for AI usage (leave empty for no limit).
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
          
          <FormField
            control={form.control}
            name="defaultOptimizationStrategy"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Default Optimization Strategy</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl>
                    <SelectTrigger className="bg-white">
                      <SelectValue placeholder="Select optimization strategy" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="cost_first">Cost First</SelectItem>
                    <SelectItem value="balanced">Balanced</SelectItem>
                    <SelectItem value="performance_first">Performance First</SelectItem>
                  </SelectContent>
                </Select>
                <FormDescription>
                  Choose how to balance cost vs. performance for AI operations.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
          
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isSubmitting ? "Updating..." : "Update Organization"}
          </Button>
        </form>
      </Form>
    </div>
  )
}
