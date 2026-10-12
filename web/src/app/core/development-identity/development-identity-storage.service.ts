import { Injectable, signal } from '@angular/core';

export type DevelopmentPrincipalKind = 'user' | 'service';

export interface DevelopmentIdentity {
  principalId: string;
  principalKind: DevelopmentPrincipalKind;
  issuer: string;
  subject: string;
  groupIds: string;
}

const storageKey = 'odip.development-identity';
const defaultIdentity: DevelopmentIdentity = {
  principalId: 'dev-user',
  principalKind: 'user',
  issuer: 'https://development.identity.local',
  subject: 'dev-user',
  groupIds: 'grp_e2987e192a0a41b4a0273c71c14fef47',
};

@Injectable({ providedIn: 'root' })
export class DevelopmentIdentityStorage {
  readonly identity = signal<DevelopmentIdentity>(this.load());

  save(identity: DevelopmentIdentity): void {
    const normalized = {
      ...identity,
      principalId: identity.principalId.trim(),
      issuer: identity.issuer.trim(),
      subject: identity.subject.trim(),
      groupIds: identity.groupIds.trim(),
    };
    localStorage.setItem(storageKey, JSON.stringify(normalized));
    this.identity.set(normalized);
  }

  private load(): DevelopmentIdentity {
    try {
      const stored = localStorage.getItem(storageKey);
      if (!stored) {
        return defaultIdentity;
      }
      const value: unknown = JSON.parse(stored);
      if (!isDevelopmentIdentity(value)) {
        return defaultIdentity;
      }
      return value;
    } catch {
      return defaultIdentity;
    }
  }
}

function isDevelopmentIdentity(value: unknown): value is DevelopmentIdentity {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return typeof candidate['principalId'] === 'string' &&
    (candidate['principalKind'] === 'user' || candidate['principalKind'] === 'service') &&
    typeof candidate['issuer'] === 'string' &&
    typeof candidate['subject'] === 'string' &&
    typeof candidate['groupIds'] === 'string';
}
