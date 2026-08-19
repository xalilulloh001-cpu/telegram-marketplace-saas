export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-2 p-8">
      <h1 className="text-2xl font-semibold">Marketplace — Customer App</h1>
      <p className="text-sm text-gray-500">Phase 1 — foundation. API: {process.env.NEXT_PUBLIC_API_BASE_URL ?? "not set"}</p>
    </main>
  );
}
