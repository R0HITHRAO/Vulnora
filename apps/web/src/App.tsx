import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stars, Text } from "@react-three/drei";
import * as THREE from "three";
import { Suspense, useMemo, useState } from "react";
import "./styles.css";

type FindingSeverity = "critical" | "high" | "medium";

type Finding = {
  id: string;
  title: string;
  category: string;
  severity: FindingSeverity;
  position: [number, number, number];
  evidence_status?: string;
};

const demoFindings: Finding[] = [
  {
    id: "F-001",
    title: "Retrieved context can override system intent",
    category: "Prompt injection",
    severity: "critical",
    position: [2.6, 0.8, 0.2],
  },
  {
    id: "F-002",
    title: "Sensitive source metadata appears in responses",
    category: "Sensitive information disclosure",
    severity: "high",
    position: [-2.4, -0.4, 0.3],
  },
  {
    id: "F-003",
    title: "Tool permissions exceed the declared scope",
    category: "Excessive agency",
    severity: "medium",
    position: [0.7, 1.7, -0.4],
  },
];

type ScanResponse = {
  scan_id: string;
  status: "queued" | "running" | "completed" | "failed";
  target_name: string;
  tests_run: number;
  findings: Array<Omit<Finding, "position">>;
};

const positions: Array<[number, number, number]> = [
  [2.6, 0.8, 0.2],
  [-2.4, -0.4, 0.3],
  [0.7, 1.7, -0.4],
];

function FindingNode({
  finding,
  onSelect,
}: {
  finding: Finding;
  onSelect: (finding: Finding) => void;
}) {
  const color = {
    critical: "#ff4d6d",
    high: "#ff9f43",
    medium: "#ffd166",
  }[finding.severity];

  return (
    <group position={finding.position} onClick={() => onSelect(finding)}>
      <mesh>
        <sphereGeometry args={[0.22, 24, 24]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={1.8} />
      </mesh>
      <Text position={[0, 0.42, 0]} fontSize={0.14} color="white" anchorX="center">
        {finding.id}
      </Text>
    </group>
  );
}

function SecurityUniverse({
  findings,
  onSelect,
}: {
  findings: Finding[];
  onSelect: (finding: Finding) => void;
}) {
  const lines = useMemo(
    () =>
      findings.map((finding) => ({
        from: [0, 0, 0] as [number, number, number],
        to: finding.position,
      })),
    [findings],
  );

  return (
    <>
      <ambientLight intensity={0.65} />
      <pointLight position={[4, 4, 4]} intensity={12} color="#7c83fd" />
      <Stars radius={40} depth={20} count={1200} factor={2} saturation={0} fade />
      <mesh>
        <icosahedronGeometry args={[1.1, 3]} />
        <meshStandardMaterial color="#5b5de6" emissive="#24245d" emissiveIntensity={1.2} wireframe />
      </mesh>
      <Text position={[0, -1.55, 0]} fontSize={0.2} color="#cdd2ff" anchorX="center">
        AUTHORIZED TARGET
      </Text>
      {lines.map((line, index) => (
        <line key={index}>
          <bufferGeometry attach="geometry" setFromPoints={[line.from, line.to].map((point) => new THREE.Vector3(...point))} />
          <lineBasicMaterial attach="material" color="#6c72ff" transparent opacity={0.55} />
        </line>
      ))}
      {findings.map((finding) => (
        <FindingNode key={finding.id} finding={finding} onSelect={onSelect} />
      ))}
    </>
  );
}

export function App() {
  const [findings, setFindings] = useState<Finding[]>(demoFindings);
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(demoFindings[0]);
  const [scanStatus, setScanStatus] = useState("Demo findings loaded");
  const [isStartingScan, setIsStartingScan] = useState(false);

  async function startAuthorizedScan() {
    setIsStartingScan(true);
    setScanStatus("Submitting authorized scan...");
    try {
      const response = await fetch("http://localhost:8000/api/v1/scans", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target: {
            name: "Demo RAG Application",
            target_type: "rag",
            base_url: "http://localhost:8000",
            environment: "development",
          },
          authorization: {
            signed_by: "local-developer",
            allowed_hostnames: ["localhost"],
            approved_categories: ["prompt_injection", "disclosure", "agency"],
            max_requests: 100,
            max_concurrency: 2,
            emergency_stop_contact: "local-developer",
            expires_at: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
          },
          categories: ["prompt_injection", "disclosure", "agency"],
          safe_test_mode: true,
        }),
      });
      if (!response.ok) {
        throw new Error(`Scan request failed (${response.status})`);
      }
      const { scan_id } = (await response.json()) as { scan_id: string };
      const scanResponse = await fetch(`http://localhost:8000/api/v1/scans/${scan_id}`);
      if (!scanResponse.ok) {
        throw new Error(`Scan status request failed (${scanResponse.status})`);
      }
      const scan = (await scanResponse.json()) as ScanResponse;
      const hydratedFindings = scan.findings.map((finding, index) => ({
        ...finding,
        position: positions[index % positions.length],
      }));
      setFindings(hydratedFindings);
      setSelectedFinding(hydratedFindings[0] ?? null);
      setScanStatus(`Scan ${scan.status} · ${scan.tests_run} tests`);
    } catch (error) {
      setScanStatus(error instanceof Error ? error.message : "Unable to start scan");
    } finally {
      setIsStartingScan(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">AUTONOMOUS SECURITY TESTING</p>
          <h1>Vulnora</h1>
        </div>
        <div className="scan-status">
          <span className="status-dot" />
          <span>{scanStatus}</span>
        </div>
      </header>
      <section className="dashboard">
        <aside className="panel intro-panel">
          <p className="eyebrow">TARGET / DEMO-RAG-001</p>
          <h2>Security universe</h2>
          <p className="muted">
            Explore the authorized target architecture and select a finding to inspect its evidence trail.
          </p>
          <div className="metric-grid">
            <div><strong>{findings.length ? 18 : 0}</strong><span>tests run</span></div>
            <div><strong>{findings.length}</strong><span>findings</span></div>
            <div><strong>72%</strong><span>confidence</span></div>
          </div>
          <button type="button" className="primary-button" onClick={startAuthorizedScan} disabled={isStartingScan}>
            {isStartingScan ? "Running authorized scan..." : "Run authorized demo scan"}
          </button>
        </aside>
        <div className="scene-frame">
          <Canvas camera={{ position: [0, 0.4, 7], fov: 45 }}>
            <Suspense fallback={null}>
              <SecurityUniverse findings={findings} onSelect={setSelectedFinding} />
              <OrbitControls enablePan={false} minDistance={4} maxDistance={10} />
            </Suspense>
          </Canvas>
          <div className="scene-hint">Drag to orbit · scroll to zoom · click a finding</div>
        </div>
        <aside className="panel finding-panel">
          <p className="eyebrow">SELECTED FINDING</p>
          {selectedFinding ? (
            <>
              <div className={`severity severity-${selectedFinding.severity}`}>{selectedFinding.severity}</div>
              <h2>{selectedFinding.title}</h2>
              <p className="muted">{selectedFinding.category} · OWASP GenAI LLM Top 10</p>
              <div className="evidence-box">
                <span>Evidence status</span>
                <strong>{selectedFinding.evidence_status ?? "Reproducible · 4/5 attempts"}</strong>
              </div>
              <p className="muted">Next step: review the sanitized response trace and apply the recommended mitigation before retesting.</p>
            </>
          ) : (
            <p className="muted">Select a node in the security universe.</p>
          )}
        </aside>
      </section>
    </main>
  );
}
