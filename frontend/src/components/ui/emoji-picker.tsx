'use client'

import * as React from 'react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface EmojiPickerProps {
  onEmojiSelect: (emoji: string) => void
  currentEmoji?: string
}

const commonEmojis = [
  '🤖', '🧠', '💡', '🔍', '📊', '📈', '📝', '📚',
  '💬', '🗣️', '📱', '💻', '🖥️', '⚙️', '🔧', '🛠️',
  '🧩', '🎯', '🚀', '⚡', '🔔', '📢', '🔐', '🔑',
  '📁', '📂', '📄', '📑', '📋', '📌', '📎', '🔗',
  '📧', '📨', '📩', '📤', '📥', '📬', '📭', '📮',
  '🗃️', '🗄️', '🗂️', '📰', '📃', '📜', '📓', '📒',
  '🔎', '🔏', '🔐', '🔒', '🔓', '🎤', '🔊',
]

export function EmojiPicker({ onEmojiSelect, currentEmoji = '🤖' }: EmojiPickerProps) {
  const [searchTerm, setSearchTerm] = React.useState('')
  const [open, setOpen] = React.useState(false)

  const filteredEmojis = searchTerm
    ? commonEmojis.filter(emoji => 
        emoji.includes(searchTerm) || 
        getEmojiDescription(emoji).toLowerCase().includes(searchTerm.toLowerCase()))
    : commonEmojis

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" className="h-10 px-4">
          <span className="mr-2">{currentEmoji}</span>
          <span>Select Icon</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80">
        <div className="space-y-4">
          <h4 className="font-medium">Select an emoji</h4>
          <Input 
            placeholder="Search emojis..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="mb-2"
          />
          <div className="grid grid-cols-8 gap-2">
            {filteredEmojis.map((emoji) => (
              <Button
                key={emoji}
                variant="ghost"
                className="h-10 w-10 p-0 text-xl"
                onClick={() => {
                  onEmojiSelect(emoji)
                  setOpen(false)
                }}
              >
                {emoji}
              </Button>
            ))}
          </div>
          {filteredEmojis.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-2">
              No emojis found
            </p>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}

// Helper function to provide descriptions for emojis for better search
function getEmojiDescription(emoji: string): string {
  const descriptions: Record<string, string> = {
    '🤖': 'robot ai bot assistant',
    '🧠': 'brain intelligence smart thinking',
    '💡': 'idea light bulb insight',
    '🔍': 'search find magnify glass',
    '📊': 'chart data analytics statistics',
    '📈': 'graph increase growth trending',
    '📝': 'note document write',
    '📚': 'books knowledge learning education',
    '💬': 'chat message conversation',
    '🗣️': 'speaking talk voice',
    '📱': 'phone mobile device',
    '💻': 'laptop computer',
    '🖥️': 'desktop computer monitor',
    '⚙️': 'gear settings configuration',
    '🔧': 'wrench tool fix repair',
    '🛠️': 'tools hammer wrench build',
    '🧩': 'puzzle piece solution',
    '🎯': 'target goal aim',
    '🚀': 'rocket launch fast speed',
    '⚡': 'lightning fast speed quick',
  }

  return descriptions[emoji] || ''
}
