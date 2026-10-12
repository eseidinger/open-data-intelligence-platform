import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { DevelopmentIdentityStorage } from './development-identity-storage.service';

export const developmentIdentityInterceptor: HttpInterceptorFn = (request, next) => {
  if (!request.url.startsWith('/api/')) {
    return next(request);
  }

  const identity = inject(DevelopmentIdentityStorage).identity();
  return next(request.clone({
    setHeaders: {
      'X-Platform-Principal-Id': identity.principalId,
      'X-Platform-Principal-Kind': identity.principalKind,
      'X-Platform-Principal-Issuer': identity.issuer,
      'X-Platform-Principal-Subject': identity.subject,
      'X-Platform-Principal-Group-Ids': identity.groupIds,
    },
  }));
};
