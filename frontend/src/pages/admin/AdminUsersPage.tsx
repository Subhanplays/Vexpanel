import { useState } from 'react'
import { Plus, Search, MoreVertical, Edit, Trash2, Shield, UserCheck, UserX } from 'lucide-react'
import { useAdminUsers } from '@/hooks/useApi'
import { Card, CardContent, Badge, Button, Modal, Input, Select, Skeleton, TableSkeleton } from '@/components/ui'
import { cn, getStatusColor, formatDate } from '@/utils/helpers'

export function AdminUsersPage() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingUser, setEditingUser] = useState<any>(null)
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    role: 'user',
  })

  const { data: users, isLoading } = useAdminUsers({ page, page_size: pageSize, search, role: roleFilter || undefined })

  const handleEdit = (user: any) => {
    setEditingUser(user)
    setFormData({
      username: user.username,
      email: user.email || '',
      password: '',
      role: user.role,
    })
    setShowEditModal(true)
  }

  const handleCreate = () => {
    setFormData({ username: '', email: '', password: '', role: 'user' })
    setShowCreateModal(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // Implementation would call API
    setShowCreateModal(false)
    setShowEditModal(false)
  }

  const columns = [
    { key: 'username', label: 'Username' },
    { key: 'email', label: 'Email' },
    { key: 'role', label: 'Role' },
    { key: 'status', label: 'Status' },
    { key: 'created_at', label: 'Created' },
    { key: 'actions', label: 'Actions' },
  ]

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton variant="text" width="200" />
          <Skeleton variant="rectangular" width={120} height={40} />
        </div>
        <TableSkeleton rows={5} columns={6} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-vex-text">User Management</h1>
          <p className="text-vex-textMuted">Manage user accounts and permissions</p>
        </div>
        <Button onClick={handleCreate}>
          <Plus className="h-4 w-4 mr-2" />
          Add User
        </Button>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-vex-textMuted" />
              <Input
                placeholder="Search users..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              options={[
                { value: '', label: 'All Roles' },
                { value: 'super_admin', label: 'Super Admin' },
                { value: 'admin', label: 'Admin' },
                { value: 'support', label: 'Support' },
                { value: 'read_only', label: 'Read Only' },
                { value: 'user', label: 'User' },
              ]}
              className="w-full sm:w-48"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-vex-border bg-vex-bg">
                  {columns.map((col) => (
                    <th key={col.key} className="px-6 py-3 text-left text-xs font-medium text-vex-textMuted uppercase tracking-wider">
                      {col.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-vex-border">
                {users?.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length} className="px-6 py-12 text-center text-vex-textMuted">
                      No users found
                    </td>
                  </tr>
                ) : (
                  users?.map((user) => (
                    <tr key={user.id} className="hover:bg-vex-bg/50 transition-colors">
                      <td className="px-6 py-4 font-medium text-vex-text">{user.username}</td>
                      <td className="px-6 py-4 text-vex-textMuted">{user.email || 'N/A'}</td>
                      <td className="px-6 py-4">
                        <Badge variant="default">{user.role}</Badge>
                      </td>
                      <td className="px-6 py-4">
                        <Badge className={user.is_banned ? 'badge-danger' : user.is_active ? 'badge-success' : 'badge-gray'}>
                          {user.is_banned ? 'Banned' : user.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-vex-textMuted">{formatDate(user.created_at)}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="ghost" size="sm" onClick={() => handleEdit(user)}>
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button variant="danger" size="sm">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Modal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} title="Create User" size="lg">
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Username" value={formData.username} onChange={(e) => setFormData({...formData, username: e.target.value})} required />
          <Input label="Email" type="email" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} />
          <Input label="Password" type="password" value={formData.password} onChange={(e) => setFormData({...formData, password: e.target.value})} required />
          <Select label="Role" value={formData.role} onChange={(e) => setFormData({...formData, role: e.target.value})} options={[
            { value: 'user', label: 'User' },
            { value: 'support', label: 'Support' },
            { value: 'read_only', label: 'Read Only' },
            { value: 'admin', label: 'Admin' },
            { value: 'super_admin', label: 'Super Admin' },
          ]} />
          <div className="flex justify-end gap-2 pt-4 border-t border-vex-border">
            <Button type="button" variant="secondary" onClick={() => setShowCreateModal(false)}>Cancel</Button>
            <Button type="submit">Create User</Button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={showEditModal} onClose={() => setShowEditModal(false)} title="Edit User" size="lg">
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Username" value={formData.username} onChange={(e) => setFormData({...formData, username: e.target.value})} required />
          <Input label="Email" type="email" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} />
          <Input label="New Password (Optional)" type="password" value={formData.password} onChange={(e) => setFormData({...formData, password: e.target.value})} />
          <Select label="Role" value={formData.role} onChange={(e) => setFormData({...formData, role: e.target.value})} options={[
            { value: 'user', label: 'User' },
            { value: 'support', label: 'Support' },
            { value: 'read_only', label: 'Read Only' },
            { value: 'admin', label: 'Admin' },
            { value: 'super_admin', label: 'Super Admin' },
          ]} />
          <div className="flex justify-end gap-2 pt-4 border-t border-vex-border">
            <Button type="button" variant="secondary" onClick={() => setShowEditModal(false)}>Cancel</Button>
            <Button type="submit">Save Changes</Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}