import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { LoaderCircle } from 'lucide-react';
import { cn } from '../../lib/utils';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'icon';
  loading?: boolean;
  icon?: ReactNode;
};

export function Button({
  children, className, variant = 'primary', size = 'md', loading, icon, disabled, ...props
}: Props) {
  return (
    <button
      className={cn('button', 'button-' + variant, 'button-' + size, className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <LoaderCircle size={17} className="icon-spin" /> : icon}
      {children}
    </button>
  );
}
