import React from "react";
import { z } from "zod";
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  spring,
  interpolate,
} from "remotion";

export const RundownSchema = z.object({
  date: z.string(),
  introText: z.string(),
  tickerText: z.string(),
  ctaLine1: z.string(),
  ctaLine2: z.string(),
  newsItems: z.array(
    z.object({
      title: z.string(),
      detail: z.string(),
    })
  ),
});

type RundownProps = z.infer<typeof RundownSchema>;

export const BreakingNewsRundown: React.FC<RundownProps> = ({
  date,
  introText,
  tickerText,
  ctaLine1,
  ctaLine2,
  newsItems,
}) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#1a1a2e",
        fontFamily: "Arial, sans-serif",
        color: "white",
      }}
    >
      <Sequence from={0} durationInFrames={120}>
        <AbsoluteFill
          style={{
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <h1
            style={{
              fontSize: 72,
              opacity: interpolate(frame, [0, 30], [0, 1], {
                extrapolateRight: "clamp",
              }),
            }}
          >
            DAILY RUNDOWN
          </h1>
          <p style={{ fontSize: 28, color: "#aaa" }}>{date}</p>
        </AbsoluteFill>
      </Sequence>

      <Sequence from={120} durationInFrames={180}>
        <AbsoluteFill
          style={{
            justifyContent: "center",
            alignItems: "center",
            padding: 60,
          }}
        >
          <p style={{ fontSize: 32, textAlign: "center", lineHeight: 1.6 }}>
            {introText}
          </p>
        </AbsoluteFill>
      </Sequence>

      {newsItems.map((item, index) => (
        <Sequence
          key={index}
          from={300 + index * 200}
          durationInFrames={200}
        >
          <AbsoluteFill
            style={{
              justifyContent: "center",
              padding: 80,
            }}
          >
            <h2 style={{ fontSize: 48, marginBottom: 20 }}>{item.title}</h2>
            <p style={{ fontSize: 28, color: "#ccc", lineHeight: 1.5 }}>
              {item.detail}
            </p>
          </AbsoluteFill>
        </Sequence>
      ))}

      <AbsoluteFill
        style={{
          position: "absolute",
          bottom: 0,
          height: 60,
          backgroundColor: "rgba(200,0,0,0.9)",
          justifyContent: "center",
          paddingLeft: 20,
        }}
      >
        <p style={{ fontSize: 18, margin: 0 }}>{tickerText}</p>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
