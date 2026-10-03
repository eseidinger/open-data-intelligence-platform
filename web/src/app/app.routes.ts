import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'sources',
    loadComponent: () => import('./features/sources/sources-page').then((module) => module.SourcesPageComponent),
  },
  { path: '', pathMatch: 'full', redirectTo: 'sources' },
  { path: '**', redirectTo: 'sources' },
];
