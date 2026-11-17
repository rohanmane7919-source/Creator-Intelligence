import { Link } from "react-router-dom";
import { Card, CardBody, CardHeader } from "../components/ui";

export default function ComingSoon({ item }) {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{item.label}</h1>
      <p className="mt-1 text-sm text-slate-500">{item.summary}</p>

      <Card className="mt-6">
        <CardHeader title="Not built yet" description={`Planned for Stage ${item.stage} of the build plan.`} />
        <CardBody>
          <p className="text-sm text-slate-600">This page will include:</p>
          <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm text-slate-700">
            {item.planned.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </CardBody>
      </Card>

      <Link
        to="/"
        className="mt-6 inline-block rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
      >
        Back to dashboard
      </Link>
    </div>
  );
}
