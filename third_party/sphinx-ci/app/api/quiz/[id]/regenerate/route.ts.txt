import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { generateQuizQuestions, DEFAULT_QUIZ_CONFIG } from "@/lib/claude";
import type { QuizConfig } from "@/lib/claude";
import { decrypt } from "@/lib/encryption";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  const quiz = await prisma.quiz.findUnique({
    where: { id },
    include: { team: { select: { anthropicApiKey: true, quizConfig: true } } },
  });
  if (!quiz) {
    return NextResponse.json({ error: "Quiz not found" }, { status: 404 });
  }

  if (quiz.expiresAt < new Date()) {
    return NextResponse.json({ error: "Quiz has expired" }, { status: 410 });
  }

  if (quiz.status !== "PENDING") {
    return NextResponse.json(
      { error: "Quiz cannot be regenerated in current state" },
      { status: 400 }
    );
  }

  if (quiz.attempts >= quiz.maxAttempts) {
    return NextResponse.json(
      { error: "Max attempts reached" },
      { status: 400 }
    );
  }

  if (!quiz.team.anthropicApiKey) {
    return NextResponse.json(
      { error: "No Anthropic API key configured" },
      { status: 400 }
    );
  }

  const anthropicKey = decrypt(quiz.team.anthropicApiKey);

  const config: QuizConfig = {
    ...DEFAULT_QUIZ_CONFIG,
    ...(quiz.team.quizConfig as Partial<QuizConfig> || {}),
  };

  try {
    const filesChanged = quiz.repo ? [quiz.repo] : [];
    const questions = await generateQuizQuestions(
      quiz.prTitle,
      filesChanged,
      quiz.diff,
      anthropicKey,
      config
    );

    await prisma.quiz.update({
      where: { id },
      data: {
        questions: JSON.parse(JSON.stringify(questions)),
        status: "PENDING",
      },
    });

    return NextResponse.json({ success: true, message: "New questions generated" });
  } catch (error) {
    console.error("Failed to regenerate questions:", error);
    return NextResponse.json(
      { error: "Failed to regenerate questions" },
      { status: 503 }
    );
  }
}
