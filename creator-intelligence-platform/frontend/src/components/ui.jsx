import { AlertCircle, Inbox } from "lucide-react";

export function Card({ className = "", children, ...rest }) {
  return (
    <section
      className={`rounded-xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)] ${className}`}
      {...rest}
    >
      {children}
    </section>
  );
}

export function CardHeader({ title, description, action }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
      <div className="min-w-0">
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        {description && <p className="mt-0.5 max-w-prose text-sm text-slate-500">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function CardBody({ className = "", children }) {
  return <div className={`px-5 py-4 ${className}`}>{children}</div>;
}

export function Skeleton({ className = "" }) {
  return <div aria-hidden="true" className={`animate-pulse rounded-md bg-slate-200/70 ${className}`} />;
}

export function EmptyState({ title, children, icon: Icon = Inbox }) {
  return (
    <div className="flex flex-col items-center px-4 py-8 text-center">
      <Icon className="h-6 w-6 text-slate-400" aria-hidden="true" />
      <p className="mt-2 text-sm font-medium text-slate-700">{title}</p>
      {children && <p className="mt-1 max-w-xs text-sm text-slate-500">{children}</p>}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div role="alert" className="flex flex-col items-center px-4 py-8 text-center">
      <AlertCircle className="h-6 w-6 text-red-500" aria-hidden="true" />
      <p className="mt-2 text-sm font-medium text-slate-800">Could not load this data</p>
      <p className="mt-1 max-w-sm text-sm text-slate-500">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Try again
        </button>
      )}
    </div>
  );
}
