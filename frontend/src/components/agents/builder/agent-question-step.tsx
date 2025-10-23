'use client'

import * as React from 'react'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { EmojiPicker } from '@/components/ui/emoji-picker'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Check as CheckIcon } from 'lucide-react'

// Define the question types
type QuestionType = 'role' | 'problem' | 'users' | 'style' | 'capabilities'

// Define the answers interface
interface AgentAnswers {
  name: string
  icon: string
  primaryRole: string
  problemStatement: string
  targetUsers: string[]
  communicationStyle: string
  outputFormat: string
  qualityPreference: number
  capabilities: string[]
}

interface AgentQuestionStepProps {
  title: string
  description: string
  questionType: QuestionType
  answers: AgentAnswers
  updateAnswers: (updates: Partial<AgentAnswers>) => void
}

// Define the role options
const roleOptions = [
  { value: 'ASSISTANT', label: 'Assistant', description: 'Helps users with general tasks and questions' },
  { value: 'ANALYZER', label: 'Analyzer', description: 'Analyzes data and provides insights' },
  { value: 'CLASSIFIER', label: 'Classifier', description: 'Categorizes and organizes information' },
  { value: 'GENERATOR', label: 'Generator', description: 'Creates content based on specifications' },
  { value: 'MONITOR', label: 'Monitor', description: 'Tracks and reports on specific metrics or events' },
]

// Define the user types
const userTypeOptions = [
  'Technical Users',
  'Non-Technical Users',
  'Customers',
  'Team Members',
  'Managers',
  'Developers',
  'Analysts',
  'Everyone',
]

// Define the communication style options
const communicationStyleOptions = [
  { value: 'PROFESSIONAL', label: 'Professional', description: 'Formal and business-like' },
  { value: 'FRIENDLY', label: 'Friendly', description: 'Warm and approachable' },
  { value: 'TECHNICAL', label: 'Technical', description: 'Detailed and precise' },
  { value: 'CONCISE', label: 'Concise', description: 'Brief and to the point' },
]

// Define the output format options
const outputFormatOptions = [
  { value: 'STRUCTURED_SUMMARY', label: 'Structured Summary', description: 'Organized with clear sections' },
  { value: 'BULLET_POINTS', label: 'Bullet Points', description: 'Concise list format' },
  { value: 'DETAILED_REPORT', label: 'Detailed Report', description: 'Comprehensive and thorough' },
  { value: 'MARKDOWN', label: 'Markdown', description: 'Formatted with markdown syntax' },
]

// Define the quality preference options
const qualityPreferenceOptions = [
  { value: 1, label: 'Speed', description: 'Optimize for faster responses' },
  { value: 2, label: 'Balanced', description: 'Balance between speed and quality' },
  { value: 3, label: 'Quality', description: 'Optimize for higher quality responses' },
]

// Define the capability options
const capabilityOptions = [
  { value: 'Text Generation', description: 'Generate human-like text responses' },
  { value: 'Code Generation', description: 'Write and explain code in various languages' },
  { value: 'Data Analysis', description: 'Analyze and interpret data sets' },
  { value: 'Image Recognition', description: 'Identify and describe images' },
  { value: 'Document Processing', description: 'Extract and process information from documents' },
  { value: 'Web Browsing', description: 'Search and retrieve information from the web' },
  { value: 'API Integration', description: 'Connect with external services and APIs' },
  { value: 'Knowledge Base Access', description: 'Access and utilize specialized knowledge bases' },
]

export function AgentQuestionStep({
  title,
  description,
  questionType,
  answers,
  updateAnswers,
}: AgentQuestionStepProps) {
  // Render the appropriate question form based on the question type
  const renderQuestionForm = () => {
    switch (questionType) {
      case 'role':
        return (
          <div className="space-y-6">
            {/* Agent Name and Icon in same row */}
            <div className="flex flex-col md:flex-row md:items-start md:gap-8">
              {/* Agent Name */}
              <div className="space-y-2 flex-1">
                <Label htmlFor="name">Name your agent</Label>
                <Input
                  id="name"
                  placeholder="E.g., Research Assistant, Code Helper, etc."
                  value={answers.name}
                  onChange={(e) => updateAnswers({ name: e.target.value })}
                />
              </div>
              
              {/* Agent Icon */}
              <div className="space-y-2 mt-4 md:mt-0">
                <Label htmlFor="icon">Choose an icon</Label>
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center text-3xl">
                    {answers.icon || '🤖'}
                  </div>
                  <EmojiPicker
                    onEmojiSelect={(emoji) => updateAnswers({ icon: emoji })}
                    currentEmoji={answers.icon}
                  />
                </div>
              </div>
            </div>
            
            {/* Primary Role */}
            <div className="space-y-3">
              <Label>Select a primary role</Label>
              <RadioGroup
                value={answers.primaryRole}
                onValueChange={(value: string) => updateAnswers({ primaryRole: value })}
                className="grid grid-cols-1 md:grid-cols-2 gap-3"
              >
                {roleOptions.map((role) => (
                  <div
                    key={role.value}
                    className={`flex items-start space-x-3 border rounded-md p-4 cursor-pointer transition-colors ${answers.primaryRole === role.value ? 'border-primary bg-primary/5' : 'hover:bg-muted'}`}
                    onClick={() => updateAnswers({ primaryRole: role.value })}
                  >
                    <RadioGroupItem value={role.value} id={`role-${role.value}`} className="mt-1" />
                    <div className="space-y-1">
                      <Label htmlFor={`role-${role.value}`} className="font-medium cursor-pointer">
                        {role.label}
                      </Label>
                      <p className="text-sm text-muted-foreground">{role.description}</p>
                    </div>
                  </div>
                ))}
              </RadioGroup>
            </div>
          </div>
        )
        
      case 'problem':
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="problemStatement">Describe the problem your agent will solve</Label>
              <Textarea
                id="problemStatement"
                placeholder="E.g., Help users research academic papers and summarize key findings, or Assist developers with debugging code and explaining solutions..."
                value={answers.problemStatement}
                onChange={(e) => updateAnswers({ problemStatement: e.target.value })}
                rows={5}
              />
              <p className="text-sm text-muted-foreground">
                Be specific about what tasks your agent will perform and what value it will provide to users.
              </p>
            </div>
          </div>
        )
        
      case 'users':
        return (
          <div className="space-y-4">
            <Label>Who will be using this agent?</Label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {userTypeOptions.map((userType) => {
                const isSelected = answers.targetUsers.includes(userType)
                return (
                  <div
                    key={userType}
                    className={`flex items-center space-x-2 border rounded-md p-3 cursor-pointer transition-colors ${isSelected ? 'border-primary bg-primary/5' : 'hover:bg-muted'}`}
                    onClick={() => {
                      if (isSelected) {
                        updateAnswers({ targetUsers: answers.targetUsers.filter(u => u !== userType) })
                      } else {
                        updateAnswers({ targetUsers: [...answers.targetUsers, userType] })
                      }
                    }}
                  >
                    <div className={`flex h-5 w-5 items-center justify-center rounded-sm border ${isSelected ? 'bg-primary border-primary' : 'border-primary/20'}`}>
                      {isSelected && <CheckIcon className="h-3.5 w-3.5 text-primary-foreground" />}
                    </div>
                    <span>{userType}</span>
                  </div>
                )
              })}
            </div>
            <p className="text-sm text-muted-foreground">
              Select all that apply. This helps tailor the agent's communication style and capabilities.
            </p>
          </div>
        )
        
      case 'style':
        return (
          <div className="space-y-6">
            {/* Communication Style */}
            <div className="space-y-3">
              <Label>Communication Style</Label>
              <RadioGroup
                value={answers.communicationStyle}
                onValueChange={(value: string) => updateAnswers({ communicationStyle: value })}
                className="grid grid-cols-1 md:grid-cols-2 gap-3"
              >
                {communicationStyleOptions.map((style) => (
                  <div
                    key={style.value}
                    className={`flex items-start space-x-3 border rounded-md p-4 cursor-pointer transition-colors ${answers.communicationStyle === style.value ? 'border-primary bg-primary/5' : 'hover:bg-muted'}`}
                    onClick={() => updateAnswers({ communicationStyle: style.value })}
                  >
                    <RadioGroupItem value={style.value} id={`style-${style.value}`} className="mt-1" />
                    <div className="space-y-1">
                      <Label htmlFor={`style-${style.value}`} className="font-medium cursor-pointer">
                        {style.label}
                      </Label>
                      <p className="text-sm text-muted-foreground">{style.description}</p>
                    </div>
                  </div>
                ))}
              </RadioGroup>
            </div>
            
            {/* Output Format */}
            <div className="space-y-3">
              <Label>Output Format</Label>
              <Select
                value={answers.outputFormat}
                onValueChange={(value: string) => updateAnswers({ outputFormat: value })}
              >
                <SelectTrigger className="max-w-md">
                  <SelectValue placeholder="Select an output format" />
                </SelectTrigger>
                <SelectContent>
                  {outputFormatOptions.map((format) => (
                    <SelectItem key={format.value} value={format.value}>
                      <div className="flex flex-col">
                        <span>{format.label}</span>
                        <span className="text-xs text-muted-foreground">{format.description}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            {/* Quality Preference */}
            <div className="space-y-3">
              <Label>Quality vs. Speed Preference</Label>
              <RadioGroup
                value={answers.qualityPreference.toString()}
                onValueChange={(value: string) => updateAnswers({ qualityPreference: parseInt(value) })}
                className="grid grid-cols-1 md:grid-cols-3 gap-3"
              >
                {qualityPreferenceOptions.map((option) => (
                  <div
                    key={option.value}
                    className={`flex items-start space-x-3 border rounded-md p-4 cursor-pointer transition-colors ${answers.qualityPreference === option.value ? 'border-primary bg-primary/5' : 'hover:bg-muted'}`}
                    onClick={() => updateAnswers({ qualityPreference: option.value })}
                  >
                    <RadioGroupItem value={option.value.toString()} id={`quality-${option.value}`} className="mt-1" />
                    <div className="space-y-1">
                      <Label htmlFor={`quality-${option.value}`} className="font-medium cursor-pointer">
                        {option.label}
                      </Label>
                      <p className="text-sm text-muted-foreground">{option.description}</p>
                    </div>
                  </div>
                ))}
              </RadioGroup>
            </div>
          </div>
        )
        
      case 'capabilities':
        return (
          <div className="space-y-4">
            <Label>Select capabilities for your agent</Label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {capabilityOptions.map((capability) => {
                const isSelected = answers.capabilities.includes(capability.value)
                return (
                  <div
                    key={capability.value}
                    className={`flex items-start space-x-3 border rounded-md p-4 cursor-pointer transition-colors ${isSelected ? 'border-primary bg-primary/5' : 'hover:bg-muted'}`}
                    onClick={() => {
                      if (isSelected) {
                        updateAnswers({ capabilities: answers.capabilities.filter(c => c !== capability.value) })
                      } else {
                        updateAnswers({ capabilities: [...answers.capabilities, capability.value] })
                      }
                    }}
                  >
                    <div className={`flex h-5 w-5 items-center justify-center rounded-sm border ${isSelected ? 'bg-primary border-primary' : 'border-primary/20'}`}>
                      {isSelected && <CheckIcon className="h-3.5 w-3.5 text-primary-foreground" />}
                    </div>
                    <div className="space-y-1">
                      <span className="font-medium">{capability.value}</span>
                      <p className="text-sm text-muted-foreground">{capability.description}</p>
                    </div>
                  </div>
                )
              })}
            </div>
            <p className="text-sm text-muted-foreground">
              Select all capabilities that your agent will need. Each capability enables specific functionality.
            </p>
          </div>
        )
        
      default:
        return null
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold">{title}</h2>
        <p className="text-muted-foreground">{description}</p>
      </div>
      
      <div className="py-4">{renderQuestionForm()}</div>
    </div>
  )
}
