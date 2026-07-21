import type { CapabilityItem, TaxonomyItem, WorkItem } from "./types";

export type TReferenceField =
  | "work-parent" | "work-initiative" | "work-blockers"
  | "taxonomy-parent" | "taxonomy-relates" | "taxonomy-vocabulary"
  | "capability-feature" | "capability-subject" | "capability-roles"
  | "capability-when" | "capability-blocked-by" | "capability-planning-doc"
  | "capability-superseded-by";

export interface TReferenceOption {
  identifier: string;
  displayName: string;
}

export interface TRankedReferenceOption extends TReferenceOption {
  score: number;
}

export interface THighlightPart {
  text: string;
  matched: boolean;
}

export interface TReferenceContext {
  work: WorkItem[];
  taxonomy: TaxonomyItem[];
  capabilities: CapabilityItem[];
  currentIdentifier?: string;
  selected?: string[];
}

const RESULT_LIMIT = 10;

function option(identifier: string, displayName: string | undefined): TReferenceOption {
  return { identifier, displayName: displayName || identifier };
}

function descendantsOf(identifier: string, items: WorkItem[]): Set<string> {
  const descendants = new Set<string>();
  let changed = true;
  while (changed) {
    changed = false;
    for (const item of items) {
      if (item.parent && (item.parent === identifier || descendants.has(item.parent)) && !descendants.has(item.slug)) {
        descendants.add(item.slug); changed = true;
      }
    }
  }
  return descendants;
}

export function referenceOptions(field: TReferenceField, context: TReferenceContext): TReferenceOption[] {
  const current = context.currentIdentifier;
  const selected = new Set(context.selected ?? []);
  const work = context.work.map((item) => option(item.slug, item.title));
  const taxonomy = context.taxonomy.map((item) => option(item.qualified ?? item.slug, item.name));
  const capabilities = context.capabilities.map((item) => option(item.qualified ?? item.path, item.name));
  if (field === "work-parent") {
    const excluded = current ? descendantsOf(current, context.work) : new Set<string>();
    if (current) excluded.add(current);
    return work.filter((item) => !excluded.has(item.identifier));
  }
  if (field === "work-initiative") return context.work.filter((item) => item.type === "epic").map((item) => option(item.slug, item.title));
  if (field === "work-blockers") return work.filter((item) => item.identifier !== current && !selected.has(item.identifier));
  if (field === "taxonomy-vocabulary") return context.taxonomy.filter((item) => item.kind === "Vocabulary").map((item) => option(item.qualified ?? item.slug, item.name));
  if (field === "taxonomy-relates") return taxonomy.filter((item) => item.identifier !== current && !selected.has(item.identifier));
  if (field === "taxonomy-parent") return taxonomy;
  if (field === "capability-feature") return context.taxonomy.filter((item) => item.kind === "Feature").map((item) => option(item.qualified ?? item.slug, item.name));
  if (field === "capability-subject") return taxonomy.filter((item) => !selected.has(item.identifier));
  if (field === "capability-roles") return capabilities.filter((item) => item.identifier.startsWith("roles/") && !selected.has(item.identifier));
  if (field === "capability-when") return capabilities.filter((item) => item.identifier.startsWith("conditions/") && !selected.has(item.identifier));
  if (field === "capability-planning-doc") return work;
  return capabilities.filter((item) => item.identifier !== current && !selected.has(item.identifier));
}

export function rankReferenceOptions(options: TReferenceOption[], rawQuery: string): TRankedReferenceOption[] {
  const query = rawQuery.trim().toLocaleLowerCase();
  if (!query) return [];
  return options.flatMap((candidate) => {
    const name = candidate.displayName.toLocaleLowerCase();
    const identifier = candidate.identifier.toLocaleLowerCase();
    const nameScore = name.includes(query) ? query.length / name.length : 0;
    const identifierScore = identifier.includes(query) ? query.length / identifier.length : 0;
    if (!nameScore && !identifierScore) return [];
    return [{ ...candidate, score: (nameScore + identifierScore * 2) / 3 }];
  }).sort((left, right) => right.score - left.score
    || left.displayName.localeCompare(right.displayName)
    || left.identifier.localeCompare(right.identifier)).slice(0, RESULT_LIMIT);
}

export function highlightMatches(value: string, rawQuery: string): THighlightPart[] {
  const query = rawQuery.trim();
  if (!query) return [{ text: value, matched: false }];
  const lowerValue = value.toLocaleLowerCase();
  const lowerQuery = query.toLocaleLowerCase();
  const parts: THighlightPart[] = [];
  let cursor = 0;
  while (cursor < value.length) {
    const index = lowerValue.indexOf(lowerQuery, cursor);
    if (index < 0) { parts.push({ text: value.slice(cursor), matched: false }); break; }
    if (index > cursor) parts.push({ text: value.slice(cursor, index), matched: false });
    parts.push({ text: value.slice(index, index + query.length), matched: true });
    cursor = index + query.length;
  }
  return parts;
}
