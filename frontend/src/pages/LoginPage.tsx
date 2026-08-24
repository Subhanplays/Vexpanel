import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { Lock, Mail, Eye, EyeOff, AlertCircle } from 'lucide-react'
import { useAuthStore } from '@/hooks/useAuth'
import { useLogin } from '@/hooks/useApi'
import { Button, Input, Card, CardContent, Alert } from '@/components/ui'

export function LoginPage() {
  const navigate = useNavigate()
  const { setUser } = useAuthStore()
  const { mutate: login, isPending, error: apiError } = useLogin()
  const [showPassword, setShowPassword] = useState(false)
  const [generalError, setGeneralError] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<{ username: string; password: string }>()

  const onSubmit = (data: { username: string; password: string }) => {
    setGeneralError('')
    login(data, {
      onSuccess: async (response) => {
        try {
          const { data: user } = await import('@/utils/api').then(m => m.default.get('/auth/me'))
          setUser(user)
          navigate('/dashboard')
        } catch {
          navigate('/dashboard')
        }
      },
      onError: (err) => {
        setGeneralError(err.message || 'Login failed')
      },
    })
  }

  return (
    <div className="w-full max-w-md mx-auto">
      <Card>
        <CardContent className="p-6">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-vex-text">Welcome back</h1>
            <p className="text-vex-textMuted mt-1">Sign in to your VexPanel account</p>
          </div>

          {(generalError || apiError) && (
            <Alert variant="danger" className="mb-6" onClose={() => setGeneralError('')}>
              {generalError || apiError?.message || 'Login failed'}
            </Alert>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Username"
              placeholder="Enter your username"
              type="text"
              autoComplete="username"
              error={errors.username?.message}
              {...register('username', { required: 'Username is required' })}
              leftIcon={<Mail className="h-5 w-5 text-vex-textMuted" />}
            />

            <Input
              label="Password"
              placeholder="Enter your password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              error={errors.password?.message}
              {...register('password', { required: 'Password is required' })}
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

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" className="rounded border-vex-border text-vex-primary focus:ring-vex-primary" />
                <span className="text-sm text-vex-textMuted">Remember me</span>
              </label>
              <Link to="/forgot-password" className="text-sm text-vex-primary hover:underline">
                Forgot password?
              </Link>
            </div>

            <Button type="submit" className="w-full" size="lg" loading={isPending}>
              Sign in
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-vex-textMuted">
            Don't have an account?{' '}
            <Link to="/register" className="text-vex-primary hover:underline font-medium">
              Sign up
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}