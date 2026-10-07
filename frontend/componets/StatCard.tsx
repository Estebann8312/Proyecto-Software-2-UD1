type StatCardProps = {
  title: string;
  value: string;
  description: string;
  icon: string;
  color: string;
};

export default function StatCard({
  title,
  value,
  description,
  icon,
  color
}: StatCardProps) {
  return (
    <article className="stat-card">
      <div className={`stat-icon ${color}`}>{icon}</div>

      <div>
        <p className="stat-title">{title}</p>
        <h2>{value}</h2>
        <p className="stat-description">{description}</p>
      </div>
    </article>
  );
}