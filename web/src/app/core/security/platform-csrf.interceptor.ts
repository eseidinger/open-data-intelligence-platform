import { HttpInterceptorFn } from '@angular/common/http';

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);
const CSRF_COOKIE = '__Host-platform-csrf';

function cookieValue(name: string): string | undefined {
  const prefix = `${encodeURIComponent(name)}=`;
  const cookie = document.cookie
    .split(';')
    .map((value) => value.trim())
    .find((value) => value.startsWith(prefix));

  return cookie ? decodeURIComponent(cookie.substring(prefix.length)) : undefined;
}

export const platformCsrfInterceptor: HttpInterceptorFn = (request, next) => {
  if (!request.url.startsWith('/api/') || SAFE_METHODS.has(request.method)) {
    return next(request);
  }

  const token = cookieValue(CSRF_COOKIE);
  return next(token
    ? request.clone({ setHeaders: { 'X-Platform-CSRF-Token': token } })
    : request);
};
