"use client";
import { MotionConfig as FramerMotionConfig } from "framer-motion";
export function MotionConfig({ children }: { children: React.ReactNode }) {
  return <FramerMotionConfig reducedMotion="user">{children}</FramerMotionConfig>;
}
