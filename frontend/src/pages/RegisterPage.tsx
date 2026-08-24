import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { Mail, Lock, User, Eye, EyeOff, AlertCircle } from 'lucide-react'
import { useRegister } from '@/hooks/useApi'
import { Button, Input, Card, CardContent, Alert } from '@/components/ui'

export function RegisterPage() {
  const navigate = useNavigate()
  const { mutate: register, isPending, error: apiError } = useRegister()
  const [showPassword, setShowPassword] = useState(false)
  const [generalError, setGeneralError] = useState('')

  const {
    register: registerField,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<{
    username: string
    email: string
    password: string
    confirmPassword: string
  }>()

  const password = watch('password')

  const onSubmit = (data: {
    username: string
    email: string
    password: string
    confirmPassword: string
  }) => {
    setGeneralError('')
    register(
      { username: data.username, email: data.email, password: data.password },
      {
        onSuccess: () => {
          navigate('/login?registered=true')
        },
        onError: (err) => {
          setGeneralError(err.message || 'Registration failed')
        },
      }
    )
  }

  return (
    <div className="w-full max-w-md mx-auto">
      <Card>
        <CardContent className="p-6">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-vex-text">Create account</h1>
            <p className="text-vex-textMuted mt-1">Start managing your VPS infrastructure</p>
          </div>

          {(generalError || apiError) && (
            <Alert variant="danger" className="mb-6" onClose={() => setGeneralError('')}>
              {generalError || apiError?.message || 'Registration failed'}
            </Alert>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Username"
              placeholder="Choose a username"
              type="text"
              autoComplete="username"
              error={errors.username?.message}
              {...registerField('username', {
                required: 'Username is required',
                minLength: { value: 3, message: 'Username must be at least 3 characters' },
                maxLength: { value: 64, message: 'Username must be less than 64 characters' },
              })}
              leftIcon={<User className="h-5 w-5 text-vex-textMuted" />}
            />

            <Input
              label="Email"
              placeholder="your@email.com"
              type="email"
              autoComplete="email"
              error={errors.email?.message}
              {...registerField('email', {
                required: 'Email is required',
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: 'Invalid email address',
                },
              })}
              leftIcon={<Mail className="h-5 w-5 text-vex-textMuted" />}
            />

            <Input
              label="Password"
              placeholder="Create a password (min 12 characters)"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              error={errors.password?.message}
              {...registerField('password', {
                required: 'Password is required',
                minLength: { value: 12, message: 'Password must be at least 12 characters' },
              })}
              leftIcon={<Lock className="h-5 w-5 text-vex-textMuted" />}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-vex-textMuted hover:text-vex-text"
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              }
            />

            <Input
              label="Confirm Password"
              placeholder="Confirm your password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              error={errors.confirmPassword?.message}
              {...registerField('confirmPassword', {
                required: 'Please confirm your password',
                validate: (value) => value === password || 'Passwords do not match',
              })}
              leftIcon={<Lock className="h-5 w-5 text-vex-textMuted" />}
            />

            <Button type="submit" className="w-full" size="lg" loading={isPending}>
              Create account
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-vex-textMuted">
            Already have an account?{' '}
            <Link to="/login" className="text-vex-primary hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}