
import { Button } from '@/components/ui/button'

export default function SettingsPage() {
    return (
        <div className="p-8">
            <h1 className="text-2xl font-bold mb-4">Settings</h1>
            <p>Settings page placeholder</p>
            <Button variant="outline" className="mt-4" onClick={() => window.location.href = '/login'}>
                Logout (Placeholder)
            </Button>
        </div>
    )
}
