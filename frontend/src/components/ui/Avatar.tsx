interface AvatarProps {
  name: string;
  size?: number;
}

export default function Avatar({ name, size = 34 }: AvatarProps) {
  const initials = name
    .split(' ')
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
  return (
    <div
      style={{ width: size, height: size }}
      className="flex items-center justify-center rounded-full border border-signal-500/40 bg-gradient-to-br from-signal-600 to-signal-500 text-xs font-semibold text-void"
    >
      {initials}
    </div>
  );
}
