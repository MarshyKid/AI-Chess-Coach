import type { PatternSummary, WeaknessProfileSummary } from "../types";

interface ProfileGroup {
  key: keyof WeaknessProfileSummary;
  label: string;
  tone: "green" | "blue" | "red" | "yellow";
  emptyNote: string;
}

const GROUPS: ProfileGroup[] = [
  {
    key: "weaknesses",
    label: "Work on this",
    tone: "red",
    emptyNote: "No recurring weaknesses in this game.",
  },
  {
    key: "recurring_themes",
    label: "Keeps coming up",
    tone: "yellow",
    emptyNote: "No repeated themes yet.",
  },
  {
    key: "strengths",
    label: "Going well",
    tone: "green",
    emptyNote: "Nothing stood out as a strength this time.",
  },
  {
    key: "execution_strengths",
    label: "Well executed",
    tone: "blue",
    emptyNote: "No cleanly converted chances spotted.",
  },
];

function PatternChip({ pattern, tone }: { pattern: PatternSummary; tone: string }) {
  return (
    <li className={`chip chip--${tone}`}>
      <span className="chip__name">{pattern.display_name}</span>
      <span className="chip__count">
        ×{pattern.frequency}
      </span>
    </li>
  );
}

export function ProfileBoard({ profile }: { profile: WeaknessProfileSummary }) {
  const isEmpty = GROUPS.every((group) => profile[group.key].length === 0);

  return (
    <section className="panel">
      <div className="panel__heading">
        <h2>Player profile</h2>
        <p className="panel__hint">
          Patterns the detectors verified across this game.
        </p>
      </div>

      {isEmpty ? (
        <p className="profile__empty">
          A clean sheet — no verified patterns either way. Try a longer or
          messier game.
        </p>
      ) : (
        <div className="profile__groups">
          {GROUPS.map((group) => (
            <div key={group.key} className={`profile__group profile__group--${group.tone}`}>
              <h3>{group.label}</h3>
              {profile[group.key].length === 0 ? (
                <p className="profile__none">{group.emptyNote}</p>
              ) : (
                <ul className="profile__chips">
                  {profile[group.key].map((pattern) => (
                    <PatternChip
                      key={pattern.pattern_type}
                      pattern={pattern}
                      tone={group.tone}
                    />
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
