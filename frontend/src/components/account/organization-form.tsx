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
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { toast } from "@/components/ui/use-toast"
import { updateOrganization } from "@/lib/api/organization-api"
import { Loader2 } from "lucide-react"

const organizationFormSchema = z.object({
  name: z.string().min(2, {
    message: "Organization name must be at least 2 characters.",
  }),
  budget: z.string().refine((val) => {
    const num = parseFloat(val)
    return !isNaN(num) && num >= 0
  }, {
    message: "Budget must be a valid number.",
  }),
})

type OrganizationFormValues = z.infer<typeof organizationFormSchema>

export function OrganizationForm({ organization, setOrganization }: { 
  organization: any; 
  setOrganization: (organization: any) => void 
}) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const form = useForm<OrganizationFormValues>({
    resolver: zodResolver(organizationFormSchema) as any,
    defaultValues: {
      name: organization?.name || "",
      budget: organization?.budget ? String(organization.budget) : "0",
    },
  })

  const onSubmit: SubmitHandler<OrganizationFormValues> = async (data) => {
    if (!organization?.id) {
      toast({
        title: "Error",
        description: "Organization ID is missing. Please reload the page.",
        variant: "destructive",
      })
      return
    }
    
    setIsSubmitting(true)
    
    try {
      const updatedOrg = await updateOrganization({
        id: organization.id,
        name: data.name,
        monthly_ai_budget: parseFloat(data.budget),
        api_key_strategy: organization.api_key_strategy,
        default_optimization_strategy: organization.default_optimization_strategy
      })
      
      // Update local organization state
      setOrganization({
        ...organization,
        ...updatedOrg,
      })
      
      toast({
        title: "Organization updated",
        description: "Your organization settings have been updated successfully.",
      })
    } catch (error) {
      console.error("Error updating organization:", error)
      toast({
        title: "Error",
        description: "Failed to update organization settings. Please try again.",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit as any)} className="space-y-6">
        <FormField
          control={form.control as any}
          name="name"
          render={({ field }: { field: any }) => (
            <FormItem>
              <FormLabel>Organization Name</FormLabel>
              <FormControl>
                <Input placeholder="Your organization name" {...field} className="bg-white" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        
        <FormField
          control={form.control as any}
          name="budget"
          render={({ field }: { field: any }) => (
            <FormItem>
              <FormLabel>Monthly Budget ($)</FormLabel>
              <FormControl>
                <Input 
                  type="number" 
                  min="0" 
                  step="0.01" 
                  placeholder="0.00" 
                  {...field} 
                  className="bg-white" 
                />
              </FormControl>
              <FormDescription>
                Set your monthly budget for API usage.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        
        <div className="flex items-center space-x-4">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save changes
          </Button>
        </div>
      </form>
    </Form>
  )
}
