// "1 member", "2 members". Pass `many` for irregular words ("person", "people").
export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}
