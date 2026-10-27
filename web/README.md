# OdipWeb

This project was generated using [Angular CLI](https://github.com/angular/angular-cli) version 21.2.24.

## Dependency security

Run `npm ci` and `npm audit --audit-level=high` to reproduce CI's dependency check.
The override for `@angular/build@^21.2.24` selects `undici` 7.30.1 or a compatible
newer 7.x version because Angular's build package still pins an affected version.
The [upstream advisory](https://github.com/nodejs/undici/security/advisories/GHSA-xjj6-f33q-929c)
identifies the fix. Review and remove this override when the supported Angular
build dependency supplies a patched version itself; keep the selector aligned
with the direct dependency range. The lockfile also updates node-gyp's separate
undici 6.x dependency to 6.29.1 and fast-uri to 3.1.9.

## Development server

To start a local development server, run:

```bash
ng serve
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Vitest](https://vitest.dev/) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
