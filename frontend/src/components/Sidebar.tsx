import { NavLink, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent } from '@/components/ui/sheet';
import { FileText, History, Settings, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const navItems = [
  { path: '/', label: 'Process', icon: FileText },
  { path: '/history', label: 'History', icon: History },
  { path: '/settings', label: 'Settings', icon: Settings },
];

function SidebarContent({ onClose, showCloseButton = false }: { onClose: () => void; showCloseButton?: boolean }) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-6 border-b min-h-16">
        <h1 className="text-lg font-semibold">Tiered Email Filtering</h1>
        {showCloseButton && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Close sidebar"
            className="h-8 w-8"
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      <nav className="flex-1 py-4 overflow-y-auto" role="navigation">
        <ul className="space-y-1">
          {navItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                onClick={onClose}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-4 px-6 py-3 text-sm font-medium transition-colors border-l-[3px] border-transparent',
                    'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                    isActive && 'text-primary bg-primary/10 border-l-primary font-medium'
                  )
                }
                end={item.path === '/'}
              >
                <item.icon className="h-5 w-5 shrink-0" />
                <span className="flex-1">{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const location = useLocation();

  // Close sidebar on mobile when route changes
  useEffect(() => {
    if (window.innerWidth < 1024) {
      onClose();
    }
  }, [location, onClose]);

  return (
    <>
      {/* Desktop sidebar - always visible */}
      <aside className="hidden lg:flex fixed top-0 left-0 bottom-0 w-64 bg-background border-r flex-col z-50">
        <SidebarContent onClose={onClose} />
      </aside>

      {/* Mobile sidebar - Sheet component */}
      <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <SheetContent side="left" className="w-64 p-0">
          <SidebarContent onClose={onClose} showCloseButton />
        </SheetContent>
      </Sheet>
    </>
  );
}
