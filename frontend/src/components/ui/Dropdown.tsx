import { useState, useRef, useEffect, ReactNode } from 'react'
import { cn } from '@/utils/helpers'
import { ChevronDown, Check } from 'lucide-react'
import { Button } from './Button'

interface DropdownItem {
  label: string
  value: string
  icon?: ReactNode
  disabled?: boolean
  danger?: boolean
}

interface DropdownProps {
  trigger: ReactNode
  items: DropdownItem[]
  onSelect: (value: string) => void
  align?: 'left' | 'right'
  className?: string
}

export function Dropdown({ trigger, items, onSelect, align = 'right', className }: DropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  return (
    <div ref={dropdownRef} className={cn('relative inline-block', className)}>
      <div onClick={() => setIsOpen(!isOpen)}>{trigger}</div>
      
      {isOpen && (
        <div
          className={cn(
            'absolute z-50 mt-1 min-w-[160px] bg-vex-card rounded-lg border border-vex-border shadow-lg',
            'animate-in fade-in-0 zoom-in-95 duration-150',
            align === 'right' ? 'right-0' : 'left-0'
          )}
        >
          <ul className="py-1" role="menu">
            {items.map((item) => (
              <li key={item.value}>
                <button
                  onClick={() => {
                    onSelect(item.value)
                    setIsOpen(false)
                  }}
                  disabled={item.disabled}
                  className={cn(
                    'w-full px-4 py-2 text-left text-sm flex items-center gap-2',
                    'hover:bg-vex-border transition-colors',
                    'focus:outline-none focus:bg-vex-border',
                    item.danger ? 'text-vex-danger' : 'text-vex-text',
                    item.disabled ? 'opacity-50 cursor-not-allowed' : ''
                  )}
                  role="menuitem"
                >
                  {item.icon && <span className="flex-shrink-0">{item.icon}</span>}
                  <span className="flex-1">{item.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

interface DropdownMenuProps {
  trigger: ReactNode
  children: ReactNode
  align?: 'left' | 'right'
  className?: string
}

export function DropdownMenu({ trigger, children, align = 'right', className }: DropdownMenuProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  return (
    <div ref={dropdownRef} className={cn('relative inline-block', className)}>
      <div onClick={() => setIsOpen(!isOpen)}>{trigger}</div>
      
      {isOpen && (
        <div
          className={cn(
            'absolute z-50 mt-1 min-w-[160px] bg-vex-card rounded-lg border border-vex-border shadow-lg',
            'animate-in fade-in-0 zoom-in-95 duration-150',
            align === 'right' ? 'right-0' : 'left-0'
          )}
        >
          <div className="py-1" role="menu">
            {children}
          </div>
        </div>
      )}
    </div>
  )
}

export function DropdownItem({ children, onClick, disabled, danger, icon, className }: {
  children: ReactNode
  onClick?: () => void
  disabled?: boolean
  danger?: boolean
  icon?: ReactNode
  className?: string
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'w-full px-4 py-2 text-left text-sm flex items-center gap-2',
        'hover:bg-vex-border transition-colors',
        'focus:outline-none focus:bg-vex-border',
        danger ? 'text-vex-danger' : 'text-vex-text',
        disabled ? 'opacity-50 cursor-not-allowed' : '',
        className
      )}
      role="menuitem"
    >
      {icon && <span className="flex-shrink-0">{icon}</span>}
      <span className="flex-1">{children}</span>
    </button>
  )
}

export function DropdownDivider() {
  return <hr className="my-1 border-vex-border" />
}