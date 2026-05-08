"use client";

import { ChangeEvent, useMemo, useState } from "react";
import { motion } from "motion/react";
import { Check, Loader2, Mic2, Music2, Save, Sparkles, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { API_BASE } from "@/lib/utils";
import type { Candidate, GenerateResponse, ReferenceResponse } from "@/lib/types";

const emotions = ["기본", "츤츤", "다정", "부끄러움", "진지", "화남", "기쁨", "슬픔"];

function mediaUrl(path: string) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${API_BASE}${path}`;
}

async function readErrorMessage(response: Response) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) return data.detail.map((item: { msg?: string } | unknown) => (typeof item === "object" && item && "msg" in item ? String(item.msg) : JSON.stringify(item))).join(" / ");
  } catch {
    const text = await response.text().catch(() => "");
    if (text) return text;
  }
  return response.statusText || "요청 처리 중 오류가 발생했습니다.";
}

function parseSeconds(value: string, label: string, min: number, max?: number) {
  const normalized = value.trim();
  if (!normalized) throw new Error(`${label}를 입력하세요.`);
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed)) throw new Error(`${label}는 숫자로 입력하세요.`);
  if (parsed < min) {
    if (label === "시작 초") throw new Error("시작 초는 0 이상이어야 합니다.");
    throw new Error(`${label}는 ${min} 이상이어야 합니다.`);
  }
  if (max !== undefined && parsed > max) {
    if (label === "길이 초") throw new Error("길이 초는 3~10초 사이여야 합니다.");
    throw new Error(`${label}는 ${min}~${max}초 사이여야 합니다.`);
  }
  return parsed;
}

export default function Home() {
  const [voiceName, setVoiceName] = useState("default");
  const [lineId, setLineId] = useState("line_001");
  const [emotion, setEmotion] = useState("기본");
  const [file, setFile] = useState<File | null>(null);
  const [existingPath, setExistingPath] = useState("");
  const [startSeconds, setStartSeconds] = useState("0");
  const [durationSeconds, setDurationSeconds] = useState("9.5");
  const [text, setText] = useState("");
  const [promptText, setPromptText] = useState("");
  const [ref, setRef] = useState<ReferenceResponse | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [status, setStatus] = useState("대기 중");
  const [busy, setBusy] = useState(false);
  const [savedPath, setSavedPath] = useState("");

  const canGenerate = useMemo(() => Boolean(ref?.path && text.trim() && !busy), [ref, text, busy]);
  const hasAudioSource = Boolean(file || existingPath.trim());

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
  }

  async function makeReference() {
    if (!hasAudioSource) {
      setStatus("음성 파일이나 기존 파일 경로를 먼저 넣어주세요.");
      return;
    }
    setBusy(true);
    setStatus("참조 음성을 준비하는 중...");
    try {
      const start = parseSeconds(startSeconds, "시작 초", 0);
      const duration = parseSeconds(durationSeconds, "길이 초", 3, 10);
      const form = new FormData();
      form.append("voice_name", voiceName);
      form.append("emotion", emotion);
      form.append("start_seconds", String(start));
      form.append("duration_seconds", String(duration));
      form.append("existing_path", existingPath);
      if (file) form.append("audio_file", file);
      const response = await fetch(`${API_BASE}/api/reference`, { method: "POST", body: form });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const data = (await response.json()) as ReferenceResponse;
      setRef(data);
      setStatus(`${data.message} (${data.duration.toFixed(2)}초)`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "참조 음성을 만들지 못했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function generateVoice() {
    if (!ref) return;
    setBusy(true);
    setSavedPath("");
    setStatus("새 음성을 만드는 중... GPT-SoVITS가 처음 켜질 때는 시간이 걸릴 수 있어요.");
    try {
      const response = await fetch(`${API_BASE}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ref_audio_path: ref.path,
          voice_name: voiceName,
          emotion,
          line_id: lineId,
          text,
          prompt_text: promptText,
          candidate_count: 3,
          base_seed: 1000,
          text_lang: "ko",
          prompt_lang: "auto",
          autostart_api: true,
        }),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const data = (await response.json()) as GenerateResponse;
      setCandidates(data.candidates);
      const warningText = data.warnings?.length ? ` 주의: ${data.warnings.join(" / ")}` : "";
      setStatus(`${data.message} · ${data.candidates.length}개 음성을 만들었습니다.${warningText}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "음성 생성에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function saveCandidate(candidate: Candidate) {
    setBusy(true);
    setStatus("선택한 음성을 저장하는 중...");
    try {
      const response = await fetch(`${API_BASE}/api/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_path: candidate.ogg, voice_name: voiceName, line_id: lineId }),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const data = (await response.json()) as { path: string; message: string };
      setSavedPath(data.path);
      setStatus(data.message);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "저장에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen px-6 py-8 lg:px-10">
      <div className="mx-auto max-w-7xl space-y-8">
        <header className="flex flex-col gap-4 rounded-[2rem] border border-gray-200 bg-white p-8 shadow-sm lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-700">
              <Sparkles className="h-4 w-4" /> 로컬 음성 제작 도구
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-gray-950 md:text-5xl">Voice Lab</h1>
            <p className="text-lg leading-8 text-gray-600">음성 파일과 대사를 넣으면 원하는 느낌에 맞춰 새 음성을 만들고, 마음에 드는 결과만 저장합니다.</p>
          </div>
          <div className="rounded-2xl bg-gray-50 px-4 py-3 text-sm leading-6 text-gray-600">
            <b className="text-gray-950">사용 순서</b><br />음성 준비 → 대사 입력 → 생성 → 저장
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>1. 목소리 정보</CardTitle>
                <CardDescription>처음에는 기본값 그대로 써도 됩니다.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="space-y-2 text-sm font-medium text-gray-700">목소리 이름<Input value={voiceName} onChange={(e) => setVoiceName(e.target.value)} /></label>
                  <label className="space-y-2 text-sm font-medium text-gray-700">대사 ID<Input value={lineId} onChange={(e) => setLineId(e.target.value)} /></label>
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-medium text-gray-700">원하는 느낌</p>
                  <div className="grid grid-cols-4 gap-2">
                    {emotions.map((item) => (
                      <button key={item} onClick={() => setEmotion(item)} className={`rounded-xl border px-3 py-2 text-sm font-semibold transition ${emotion === item ? "border-indigo-600 bg-indigo-600 text-white" : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50"}`}>
                        {item}
                      </button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>2. 음성 파일</CardTitle>
                <CardDescription>긴 파일에서 3~10초 구간만 잘라 참조 음성으로 씁니다.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <label htmlFor="voice-file-input" className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 bg-gray-50 px-4 py-8 text-center transition hover:bg-gray-100">
                  <Upload className="mb-3 h-7 w-7 text-gray-500" />
                  <span className="font-semibold text-gray-900">음성 파일 선택</span>
                  <span className="mt-1 text-sm text-gray-500">{file ? `선택된 파일: ${file.name}` : "mp3, wav, ogg 파일"}</span>
                  <span className="mt-2 text-xs text-gray-400">파일을 고른 뒤 참조 음성 만들기를 눌러주세요.</span>
                </label>
                <input id="voice-file-input" type="file" accept="audio/*" className="sr-only" onChange={onFileChange} />
                <label className="space-y-2 text-sm font-medium text-gray-700">기존 파일 경로<Input value={existingPath} onChange={(e) => setExistingPath(e.target.value)} placeholder="/mnt/c/Users/Desktop/Downloads/audio.mp3" /></label>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="space-y-2 text-sm font-medium text-gray-700">시작 초<Input type="number" min="0" step="0.1" value={startSeconds} onChange={(e) => setStartSeconds(e.target.value)} /></label>
                  <label className="space-y-2 text-sm font-medium text-gray-700">길이 초<Input type="number" min="3" max="10" step="0.1" value={durationSeconds} onChange={(e) => setDurationSeconds(e.target.value)} /></label>
                </div>
                <Button variant="secondary" className="w-full" onClick={makeReference} disabled={busy || !hasAudioSource}>
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mic2 className="h-4 w-4" />} 참조 음성 만들기
                </Button>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>3. 읽힐 대사</CardTitle>
                <CardDescription>생성할 문장을 입력하세요. 참조 음성의 실제 대사를 알면 함께 적어주세요.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <label className="space-y-2 text-sm font-medium text-gray-700">읽힐 대사<Textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="이 목소리로 읽힐 대사를 입력하세요." /></label>
                <label className="space-y-2 text-sm font-medium text-gray-700">참조 음성의 실제 대사<Textarea className="min-h-20" value={promptText} onChange={(e) => setPromptText(e.target.value)} placeholder="참조 음성의 실제 대사를 모르면 비워두세요. 읽힐 대사를 여기에 다시 넣으면 품질이 나빠질 수 있어요." /></label>
                <Button size="lg" className="w-full" onClick={generateVoice} disabled={!canGenerate}>
                  {busy ? <Loader2 className="h-5 w-5 animate-spin" /> : <Music2 className="h-5 w-5" />} 새 음성 만들기
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>상태</CardTitle>
                <CardDescription>{status}</CardDescription>
              </CardHeader>
              {ref && (
                <CardContent>
                  <div className="rounded-2xl bg-gray-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-800"><Check className="h-4 w-4 text-emerald-600" /> 참조 음성 준비됨 · {ref.duration.toFixed(2)}초</div>
                    <audio controls className="w-full" src={mediaUrl(ref.url)} />
                  </div>
                </CardContent>
              )}
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>4. 마음에 드는 음성 저장</CardTitle>
                <CardDescription>가로 카드 대신 세로 목록으로 안정적으로 보여줍니다.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {candidates.length === 0 && <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 p-8 text-center text-gray-500">아직 생성된 음성이 없습니다.</div>}
                {candidates.map((candidate) => (
                  <motion.div key={`${candidate.seed}-${candidate.ogg}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <div>
                        <p className="font-semibold text-gray-950">음성 {candidate.index}</p>
                        <p className="text-xs text-gray-500">seed {candidate.seed}</p>
                      </div>
                      <Button variant="secondary" size="sm" onClick={() => saveCandidate(candidate)} disabled={busy}><Save className="h-4 w-4" /> 저장</Button>
                    </div>
                    <audio controls className="w-full" src={mediaUrl(candidate.url)} />
                  </motion.div>
                ))}
                {savedPath && <div className="rounded-xl bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">저장 위치: {savedPath}</div>}
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </main>
  );
}
