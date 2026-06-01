import React from "react";
import { Composition } from "remotion";
import {
  BreakingNewsRundown,
  RundownSchema,
} from "./videos/daily-rundown-may-9/BreakingNewsRundown";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="BreakingNewsRundown"
        component={BreakingNewsRundown}
        durationInFrames={1200}
        fps={30}
        width={1920}
        height={1080}
        schema={RundownSchema}
        defaultProps={{
          date: "16 MAI 2026",
          introText:
            "on quitte l'ere du chatbot miracle pour entrer dans celle de l'infrastructure lourde",
          tickerText:
            "BREAKING NEWS: OpenAI bascule vers GPT-5.5 Instant",
          ctaLine1: "Abonnez-vous a notre Daily Rundown",
          ctaLine2: "pour etre au courant des dernieres nouvelles!",
          newsItems: [
            {
              title: "GPT-5.5-Cyber : L'armure numerique change de camp",
              detail:
                "OpenAI vient de sortir le signal le plus clair de l'annee.",
            },
            {
              title: "Claude Mythos et le vertige du reverse engineering",
              detail:
                "Anthropic joue la carte de l'ombre avec la preview restreinte.",
            },
          ],
        }}
      />
    </>
  );
};
