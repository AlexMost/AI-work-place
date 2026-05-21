import { beforeEach, describe, expect, it, vi } from 'vitest';

const { checkText, checkFact } = vi.hoisted(() => ({
  checkText: vi.fn(),
  checkFact: vi.fn(),
}));

vi.mock('../src/core/checkText', () => ({
  checkText,
}));

vi.mock('../src/core/factCheck', () => ({
  checkFact,
}));

describe('package entrypoint', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
  });

  it('is safe to import and re-exports the feature API', async () => {
    const entrypoint = await import('../src/core/index');

    expect(entrypoint.checkText).toBe(checkText);
    expect(entrypoint.checkFact).toBe(checkFact);
    expect(checkText).not.toHaveBeenCalled();
    expect(checkFact).not.toHaveBeenCalled();
  });
});
