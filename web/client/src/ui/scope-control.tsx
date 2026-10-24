import { Flex, Select } from "@radix-ui/themes"
import { SCOPES, SCOPE_LABELS, type TScopeChoice } from "../model/scope"
import type { TProject, TScope } from "../model/types"

const EVERY = "__every__"

/** The scope control and the project filter (TCW-113 Design 6.6), matching
 * `--scope` and `--project`. Shown only when the project has a family:
 * `scopes.all` names more than one project. */
export function ScopeControl({
    scopes,
    choice,
    onChange,
}: {
    scopes: TProject["scopes"]
    choice: TScopeChoice
    onChange: (choice: TScopeChoice) => void
}) {
    if ((scopes?.all ?? []).length <= 1) return null
    const covered = scopes[choice.scope] ?? []
    return (
        <Flex gap="2" align="center" className="scope-control">
            <Select.Root
                value={choice.scope}
                onValueChange={(next) => {
                    const scope = next as TScope
                    // A project the new scope does not cover is dropped,
                    // as `--project` would refuse it.
                    const keep =
                        choice.project &&
                        (scopes[scope] ?? []).includes(choice.project)
                    onChange(
                        keep ? { scope, project: choice.project } : { scope }
                    )
                }}
            >
                <Select.Trigger aria-label="Scope" />
                <Select.Content>
                    {SCOPES.map((scope) => (
                        <Select.Item value={scope} key={scope}>
                            {`${scope}: ${SCOPE_LABELS[scope]}`}
                        </Select.Item>
                    ))}
                </Select.Content>
            </Select.Root>
            <Select.Root
                value={choice.project ?? EVERY}
                onValueChange={(next) =>
                    onChange(
                        next === EVERY
                            ? { scope: choice.scope }
                            : { scope: choice.scope, project: next }
                    )
                }
            >
                <Select.Trigger aria-label="Project" />
                <Select.Content>
                    <Select.Item value={EVERY}>All of them</Select.Item>
                    {covered.map((id) => (
                        <Select.Item value={id} key={id}>
                            {id}
                        </Select.Item>
                    ))}
                </Select.Content>
            </Select.Root>
        </Flex>
    )
}
