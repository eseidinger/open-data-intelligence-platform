import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'sources',
    loadComponent: () => import('./features/sources/sources-page').then((module) => module.SourcesPageComponent),
  },
  {
    path: 'datasets',
    loadComponent: () => import('./features/datasets/datasets-page').then((module) => module.DatasetsPageComponent),
  },
  { path: 'pipeline-runs', loadComponent: () => import('./features/pipeline-runs/pipeline-runs-page').then((module) => module.PipelineRunsPageComponent) },
  { path: '', pathMatch: 'full', redirectTo: 'sources' },
  { path: '**', redirectTo: 'sources' },
];
