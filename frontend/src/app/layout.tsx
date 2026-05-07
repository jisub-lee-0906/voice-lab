import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Voice Lab",
  description: "로컬 GPT-SoVITS 음성 제작 도구",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
