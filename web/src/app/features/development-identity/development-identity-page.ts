import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { DevelopmentIdentityStorage } from '../../core/development-identity/development-identity-storage.service';

@Component({
  selector: 'app-development-identity-page',
  imports: [ReactiveFormsModule, MatButtonModule, MatCardModule, MatFormFieldModule, MatInputModule, MatSelectModule],
  templateUrl: './development-identity-page.html',
  styleUrl: './development-identity-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DevelopmentIdentityPageComponent {
  private readonly formBuilder = inject(NonNullableFormBuilder);
  private readonly identityStorage = inject(DevelopmentIdentityStorage);
  readonly saved = this.identityStorage.identity;
  readonly form = this.formBuilder.group({
    principalId: [this.saved().principalId, Validators.required],
    principalKind: [this.saved().principalKind, Validators.required],
    issuer: [this.saved().issuer, Validators.required],
    subject: [this.saved().subject, Validators.required],
    groupIds: [this.saved().groupIds, Validators.required],
  });

  useRole(groupIds: string): void {
    this.form.controls.groupIds.setValue(groupIds);
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.identityStorage.save(this.form.getRawValue());
  }
}
