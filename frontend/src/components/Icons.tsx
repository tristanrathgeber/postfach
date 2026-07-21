// Kleine Inline-Icons (Stroke, currentColor) — keine externe Icon-Bibliothek nötig.

type IconProps = { size?: number; className?: string }

function Svg({ paths, size = 15, className }: IconProps & { paths: string[] }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {paths.map((d, i) => (
        <path key={i} d={d} />
      ))}
    </svg>
  )
}

export function PaperclipIcon(p: IconProps) {
  return (
    <Svg
      {...p}
      paths={['M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48']}
    />
  )
}

export function ArchiveIcon(p: IconProps) {
  return <Svg {...p} paths={['M21 8v13H3V8', 'M1 3h22v5H1z', 'M10 12h4']} />
}

export function TrashIcon(p: IconProps) {
  return (
    <Svg
      {...p}
      paths={['M3 6h18', 'M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6', 'M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2', 'M10 11v6', 'M14 11v6']}
    />
  )
}

export function MailIcon(p: IconProps) {
  return (
    <Svg
      {...p}
      paths={['M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z', 'M22 6l-10 7L2 6']}
    />
  )
}

export function MailOpenIcon(p: IconProps) {
  return (
    <Svg
      {...p}
      paths={[
        'M21.2 8.4c.5.38.8.97.8 1.6v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V10a2 2 0 0 1 .8-1.6l8-6a2 2 0 0 1 2.4 0l8 6Z',
        'm22 10-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 10',
      ]}
    />
  )
}

export function ReplyIcon(p: IconProps) {
  return <Svg {...p} paths={['M9 17l-5-5 5-5', 'M20 18v-2a4 4 0 0 0-4-4H4']} />
}

export function ForwardIcon(p: IconProps) {
  return <Svg {...p} paths={['m15 17 5-5-5-5', 'M4 18v-2a4 4 0 0 1 4-4h12']} />
}

export function GearIcon(p: IconProps) {
  return (
    <Svg
      {...p}
      paths={[
        'M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z',
        'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
      ]}
    />
  )
}

export function CheckIcon(p: IconProps) {
  return <Svg {...p} paths={['M4 12l5 5L20 6']} />
}

export function AlertIcon(p: IconProps) {
  return <Svg {...p} paths={['M12 9v4', 'M12 17h.01', 'M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z']} />
}

export function SearchIcon(p: IconProps) {
  return <Svg {...p} paths={['M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z', 'm21 21-4.3-4.3']} />
}

export function XIcon(p: IconProps) {
  return <Svg {...p} paths={['M18 6 6 18', 'm6 6 12 12']} />
}

export function ChevronRightIcon(p: IconProps) {
  return <Svg {...p} paths={['m9 18 6-6-6-6']} />
}

export function ChevronDownIcon(p: IconProps) {
  return <Svg {...p} paths={['m6 9 6 6 6-6']} />
}

export function SparklesIcon(p: IconProps) {
  return (
    <Svg
      {...p}
      paths={[
        'm12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z',
      ]}
    />
  )
}

export function DownloadIcon(p: IconProps) {
  return <Svg {...p} paths={['M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4', 'M7 10l5 5 5-5', 'M12 15V3']} />
}

/** Kreisförmiger Lade-Spinner. */
export function SpinnerIcon({ size = 14, className = '' }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      aria-hidden="true"
      className={`spinner ${className}`}
    >
      <path d="M12 2a10 10 0 1 0 10 10" />
    </svg>
  )
}
