const VALID_IDENTIFIER = /^[A-Za-z_][A-Za-z0-9_]*$/

/**
 * Jinja2 dot notation (`steps.foo`) only works when the step name is a valid
 * identifier. Names with spaces, leading digits, or punctuation need bracket
 * syntax (`steps['foo bar']`) instead — dot notation silently fails to parse
 * or resolve for those.
 */
export function stepRef(name: string): string {
  const safe = name || 'this_step'
  return VALID_IDENTIFIER.test(safe) ? `steps.${safe}` : `steps['${safe.replace(/'/g, "\\'")}']`
}
