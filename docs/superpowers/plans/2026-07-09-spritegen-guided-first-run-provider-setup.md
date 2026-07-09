# SpriteGen Guided First Run And Provider Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce SpriteGen's highest-confidence UX friction by making the first successful desktop path safer and making provider setup use one provider by default with role-aware image and prompt models.

**Architecture:** Keep the first implementation slice inside the existing PySide6 desktop app and local settings store. Reuse current model validation, starter project, preflight, prompt preview, and settings APIs instead of adding a new onboarding framework.

**Tech Stack:** Python 3.11+, PySide6 desktop UI, pytest, Pillow-backed test assets, existing `spritegen.projects`, `spritegen.provider_models`, and `spritegen.user_settings`.

## Global Constraints

- Do not add dependencies.
- Do not store API keys in project JSON.
- Keep provider checks offline; `Check Setup` must not make network calls.
- Preserve separate image and prompt model fields because model role validation depends on them.
- Default flow must avoid paid provider calls by using the existing `mock` provider for sample confidence checks.
- Keep advanced separate image/prompt provider setup available.
- Use existing desktop test style in `tests/spritegen/test_desktop_ui.py`.
- Keep follow-on work out of this slice: export wizard, generation QA review panel, and full multi-step wizard shell each get their own plan.

---

## Source Research Summary

Direct SpriteGen evidence:
- GitHub issue #3 asks for a unified provider setup where the user picks a provider once, image and prompt models come from role-aware lists, advanced overrides remain available, and preflight still catches wrong-role model choices.
- Local CLI preflight already reports run shape before spending image calls: project, asset, provider/model, prompt enhancement status, image count, slice count, layout summaries, and model warnings.
- The desktop app already has starter projects, prompt preview, preflight, provider settings, model suggestions, galleries, export, and variant selection, but these are exposed as many peer controls.

Adjacent public UX pain:
- Users distrust AI sprite tools when examples are weak, outputs are not truly game-ready, animations do not line up, or paid credits are wasted on unusable generations.
- Users expect "game-ready" to mean transparent/sliceable/exportable files, not only attractive images.
- Consistency, frame alignment, exact sizes, and a low-risk proof path matter more than marketing copy.

This plan implements the week-one product move: a safer first-run proof path and less provider setup duplication. Export and output QA remain separate plans because they touch different workflows and should be independently testable.

## File Structure

- Modify `src/spritegen/user_settings.py`
  - Add `shared_provider_setup: bool` to local settings so the desktop can remember whether advanced separate provider setup is shown.

- Modify `src/spritegen/ui/main_window.py`
  - Add a shared-provider mode checkbox in the Providers group.
  - Keep image and prompt model fields visible.
  - Hide prompt provider and prompt API key fields while shared-provider mode is enabled.
  - Mirror the prompt provider from the image provider in shared mode.
  - Keep role-aware image and prompt model suggestions independent.
  - Add a `Try Sample Run` button that creates the starter project under the current project root, switches providers to `mock`, and runs `Check Run`.

- Modify `tests/spritegen/test_desktop_ui.py`
  - Add regression tests for shared-provider mode default behavior, saving the mode, key handling, advanced override visibility, and the sample run path.

- Modify `README.md`
  - Document the lower-risk first-run path and the shared-provider default.

## Follow-On Plan Boundaries

These should not be implemented in this plan:
- Export wizard plan: engine target, fixed frame size, transparent background, trim/padding, selected variant, and manifest preview.
- Generation QA plan: side-by-side stage/variant comparison, consistency checklist, and per-stage regenerate controls.
- Progressive desktop shell plan: multi-step UI structure for Project -> Asset -> Output Shape -> Provider -> Generate -> Review/Export.

---

### Task 1: Persist And Apply Shared Provider Setup Mode

**Files:**
- Modify: `src/spritegen/user_settings.py:12-69`
- Modify: `src/spritegen/ui/main_window.py:520-585`
- Modify: `src/spritegen/ui/main_window.py:669-693`
- Modify: `src/spritegen/ui/main_window.py:1078-1159`
- Test: `tests/spritegen/test_desktop_ui.py`

**Interfaces:**
- Consumes: `UserSettingsStore.load() -> UserSettings`, `UserSettingsStore.save(settings: UserSettings) -> Path`, `validate_model_choice(provider: str, role: str, model: str, extra: list[ModelSuggestion], other_extra: list[ModelSuggestion]) -> ModelValidationResult`.
- Produces: `UserSettings.shared_provider_setup: bool`, `MainWindow._using_shared_provider_setup() -> bool`, `MainWindow._apply_provider_setup_mode() -> None`, `MainWindow._sync_prompt_provider_from_image_provider(reset_model: bool = True) -> None`.

- [ ] **Step 1: Write the failing shared-provider tests**

Append these tests after `test_main_window_checks_provider_setup_without_network` in `tests/spritegen/test_desktop_ui.py`:

```python
def test_main_window_uses_shared_provider_setup_by_default(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from PySide6.QtWidgets import QApplication
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))

    assert window.shared_provider_setup_check.isChecked() is True
    assert window.prompt_provider_combo.currentData() == window.image_provider_combo.currentData()
    assert window.prompt_provider_combo.isHidden() is True
    assert window.prompt_api_key_edit.isHidden() is True
    assert window.prompt_model_edit.isHidden() is False
    assert window.prompt_model_suggestions.isHidden() is False

    window._set_combo_value(window.image_provider_combo, "openrouter")
    window._on_image_provider_changed()

    assert window.prompt_provider_combo.currentData() == "openrouter"
    assert window.image_model_edit.text() == "google/gemini-3.1-flash-image-preview"
    assert window.prompt_model_edit.text() == "openai/gpt-5.5"

    window.close()
    app.processEvents()


def test_main_window_shared_provider_setup_saves_one_key(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from PySide6.QtWidgets import QApplication
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    settings_store = UserSettingsStore(tmp_path / "settings.json")
    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=settings_store)
    window._set_combo_value(window.image_provider_combo, "openrouter")
    window._on_image_provider_changed()
    window.image_api_key_edit.setText("shared-openrouter-key")

    window._on_check_provider_setup()

    assert window.status_label.text() == "Provider setup ready: image OpenRouter / prompt OpenRouter"

    window._on_save_provider_settings()
    saved = settings_store.load()

    assert saved.shared_provider_setup is True
    assert saved.image_provider == "openrouter"
    assert saved.prompt_provider == "openrouter"
    assert saved.api_key_for("openrouter") == "shared-openrouter-key"
    assert saved.api_keys == {"openrouter": "shared-openrouter-key"}

    window.close()
    app.processEvents()


def test_main_window_advanced_provider_setup_remains_available(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from PySide6.QtWidgets import QApplication
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    settings_store = UserSettingsStore(tmp_path / "settings.json")
    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=settings_store)

    window.shared_provider_setup_check.setChecked(False)
    window._set_combo_value(window.image_provider_combo, "openrouter")
    window._set_combo_value(window.prompt_provider_combo, "openai")
    window.image_api_key_edit.setText("openrouter-key")
    window.prompt_api_key_edit.setText("openai-key")

    assert window.prompt_provider_combo.isHidden() is False
    assert window.prompt_api_key_edit.isHidden() is False

    window._on_save_provider_settings()
    saved = settings_store.load()

    assert saved.shared_provider_setup is False
    assert saved.image_provider == "openrouter"
    assert saved.prompt_provider == "openai"
    assert saved.api_key_for("openrouter") == "openrouter-key"
    assert saved.api_key_for("openai") == "openai-key"

    reloaded = MainWindow(settings_store=settings_store)
    assert reloaded.shared_provider_setup_check.isChecked() is False
    assert reloaded.prompt_provider_combo.currentData() == "openai"
    assert reloaded.prompt_provider_combo.isHidden() is False
    assert reloaded.prompt_api_key_edit.isHidden() is False

    reloaded.close()
    window.close()
    app.processEvents()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/spritegen/test_desktop_ui.py::test_main_window_uses_shared_provider_setup_by_default tests/spritegen/test_desktop_ui.py::test_main_window_shared_provider_setup_saves_one_key tests/spritegen/test_desktop_ui.py::test_main_window_advanced_provider_setup_remains_available -q
```

Expected: FAIL because `MainWindow` has no `shared_provider_setup_check` and `UserSettings` has no `shared_provider_setup`.

- [ ] **Step 3: Add shared-provider mode to local settings**

In `src/spritegen/user_settings.py`, replace the `UserSettings` dataclass with this complete version. Keep `SETTINGS_SCHEMA_VERSION = 1` so existing settings files continue to load.

```python
@dataclass
class UserSettings:
    image_provider: str = "mock"
    image_model: str = "mock"
    prompt_provider: str = "mock"
    prompt_model: str = "mock"
    shared_provider_setup: bool = True
    api_keys: dict[str, str] = field(default_factory=dict)

    def api_key_for(self, provider: str) -> str:
        return self.api_keys.get(provider, "")

    def set_api_key(self, provider: str, api_key: str) -> None:
        key = api_key.strip()
        if key:
            self.api_keys[provider] = key
        else:
            self.api_keys.pop(provider, None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SETTINGS_SCHEMA_VERSION,
            "image_provider": self.image_provider,
            "image_model": self.image_model,
            "prompt_provider": self.prompt_provider,
            "prompt_model": self.prompt_model,
            "shared_provider_setup": self.shared_provider_setup,
            "api_keys": dict(self.api_keys),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserSettings":
        if data.get("version") != SETTINGS_SCHEMA_VERSION:
            return cls()
        api_keys = {
            str(provider): str(api_key)
            for provider, api_key in data.get("api_keys", {}).items()
            if api_key
        }
        return cls(
            image_provider=str(data.get("image_provider") or "mock"),
            image_model=str(data.get("image_model") or "mock"),
            prompt_provider=str(data.get("prompt_provider") or "mock"),
            prompt_model=str(data.get("prompt_model") or "mock"),
            shared_provider_setup=bool(data.get("shared_provider_setup", True)),
            api_keys=api_keys,
        )
```

- [ ] **Step 4: Add shared-provider controls to the provider form**

In `src/spritegen/ui/main_window.py`, inside `_create_left_panel`, replace the provider group construction from `config_group = QGroupBox("Providers")` through the `Prompt API Key` row with this block. Leave the model help, model catalog, provider actions, and later rows as they are.

```python
        config_group = QGroupBox("Providers")
        config_layout = QFormLayout(config_group)
        self.provider_form_layout = config_layout

        self.image_provider_combo = self._provider_combo(IMAGE_PROVIDERS)
        self.image_provider_combo.currentIndexChanged.connect(self._on_image_provider_changed)
        config_layout.addRow("Provider:", self.image_provider_combo)

        self.shared_provider_setup_check = QCheckBox("Use same provider for prompt improvement")
        self.shared_provider_setup_check.setChecked(True)
        self.shared_provider_setup_check.stateChanged.connect(self._on_shared_provider_setup_changed)
        config_layout.addRow("Provider Mode:", self.shared_provider_setup_check)

        self.image_model_edit = QLineEdit(default_model("mock", IMAGE_ROLE))
        config_layout.addRow("Image Model:", self.image_model_edit)

        self.image_model_suggestions = QComboBox()
        self.image_model_suggestions.activated.connect(
            lambda _index: self._apply_model_suggestion(IMAGE_ROLE)
        )
        config_layout.addRow("Image Suggestions:", self.image_model_suggestions)

        self.generation_variants_spin = QSpinBox()
        self.generation_variants_spin.setRange(1, 8)
        self.generation_variants_spin.setValue(1)
        config_layout.addRow("Image Variants:", self.generation_variants_spin)

        self.prompt_provider_combo = self._provider_combo(PROMPT_PROVIDERS)
        self.prompt_provider_combo.currentIndexChanged.connect(self._on_prompt_provider_changed)
        config_layout.addRow("Prompt Provider:", self.prompt_provider_combo)

        self.prompt_model_edit = QLineEdit(default_model("mock", PROMPT_ROLE))
        config_layout.addRow("Prompt Model:", self.prompt_model_edit)

        self.prompt_model_suggestions = QComboBox()
        self.prompt_model_suggestions.activated.connect(
            lambda _index: self._apply_model_suggestion(PROMPT_ROLE)
        )
        config_layout.addRow("Prompt Suggestions:", self.prompt_model_suggestions)

        self.image_api_key_edit = QLineEdit()
        self.image_api_key_edit.setEchoMode(QLineEdit.Password)
        self.image_api_key_edit.setPlaceholderText("Paste provider API key")
        self.api_key_override = self.image_api_key_edit
        config_layout.addRow("API Key:", self.image_api_key_edit)

        self.prompt_api_key_edit = QLineEdit()
        self.prompt_api_key_edit.setEchoMode(QLineEdit.Password)
        self.prompt_api_key_edit.setPlaceholderText("Paste prompt provider key")
        config_layout.addRow("Prompt API Key:", self.prompt_api_key_edit)
```

- [ ] **Step 5: Add shared-provider helper methods**

In `src/spritegen/ui/main_window.py`, add these complete methods after `_provider_combo`:

```python
    def _using_shared_provider_setup(self) -> bool:
        return bool(
            hasattr(self, "shared_provider_setup_check")
            and self.shared_provider_setup_check.isChecked()
        )

    def _set_provider_field_visible(self, widget: QWidget, visible: bool) -> None:
        widget.setVisible(visible)
        if hasattr(self, "provider_form_layout"):
            label = self.provider_form_layout.labelForField(widget)
            if label is not None:
                label.setVisible(visible)

    def _apply_provider_setup_mode(self) -> None:
        advanced_visible = not self._using_shared_provider_setup()
        self._set_provider_field_visible(self.prompt_provider_combo, advanced_visible)
        self._set_provider_field_visible(self.prompt_api_key_edit, advanced_visible)

    def _sync_prompt_provider_from_image_provider(self, reset_model: bool = True) -> None:
        provider = self.image_provider_combo.currentData()
        if self.prompt_provider_combo.currentData() != provider:
            self._set_combo_value(self.prompt_provider_combo, provider)
        self._refresh_model_suggestions(PROMPT_ROLE, provider)
        if reset_model:
            self.prompt_model_edit.setText(default_model(provider, PROMPT_ROLE))
        self._refresh_api_key_field("prompt")

    def _on_shared_provider_setup_changed(self, *_args) -> None:
        if self._using_shared_provider_setup():
            self._sync_prompt_provider_from_image_provider(reset_model=True)
            self.prompt_api_key_edit.clear()
        self._apply_provider_setup_mode()
```

- [ ] **Step 6: Update provider change handlers**

In `src/spritegen/ui/main_window.py`, replace `_on_image_provider_changed` and `_on_prompt_provider_changed` with:

```python
    def _on_image_provider_changed(self, *_args) -> None:
        provider = self.image_provider_combo.currentData()
        self._refresh_model_suggestions(IMAGE_ROLE, provider)
        self.image_model_edit.setText(default_model(provider, IMAGE_ROLE))
        if self._using_shared_provider_setup():
            self._sync_prompt_provider_from_image_provider(reset_model=True)
        self._refresh_api_key_field("image")

    def _on_prompt_provider_changed(self, *_args) -> None:
        provider = self.prompt_provider_combo.currentData()
        self._refresh_model_suggestions(PROMPT_ROLE, provider)
        self.prompt_model_edit.setText(default_model(provider, PROMPT_ROLE))
        self._refresh_api_key_field("prompt")
```

- [ ] **Step 7: Update user settings application**

In `src/spritegen/ui/main_window.py`, replace `_apply_user_settings` with:

```python
    def _apply_user_settings(self) -> None:
        self.shared_provider_setup_check.setChecked(self._user_settings.shared_provider_setup)
        self._set_combo_value(self.image_provider_combo, self._user_settings.image_provider)
        self._refresh_model_suggestions(IMAGE_ROLE, self.image_provider_combo.currentData())
        self.image_model_edit.setText(
            self._user_settings.image_model
            or default_model(self.image_provider_combo.currentData(), IMAGE_ROLE)
        )
        self._set_combo_value(self.prompt_provider_combo, self._user_settings.prompt_provider)
        if self._using_shared_provider_setup():
            self._sync_prompt_provider_from_image_provider(reset_model=False)
        self._refresh_model_suggestions(PROMPT_ROLE, self.prompt_provider_combo.currentData())
        self.prompt_model_edit.setText(
            self._user_settings.prompt_model
            or default_model(self.prompt_provider_combo.currentData(), PROMPT_ROLE)
        )
        self._refresh_api_key_fields()
        self._apply_provider_setup_mode()
```

- [ ] **Step 8: Update setup check and saving**

In `src/spritegen/ui/main_window.py`, replace `_on_check_provider_setup` and `_on_save_provider_settings` with:

```python
    def _on_check_provider_setup(self) -> None:
        missing = []
        image_provider = self.image_provider_combo.currentData()
        prompt_provider = self.prompt_provider_combo.currentData()
        validations = [
            self._validate_current_model(
                IMAGE_ROLE,
                image_provider,
                self.image_model_edit.text(),
            ),
            self._validate_current_model(
                PROMPT_ROLE,
                prompt_provider,
                self.prompt_model_edit.text(),
            ),
        ]
        model_errors = [
            validation.message
            for validation in validations
            if validation.status == MODEL_VALIDATION_ERROR
        ]
        model_warnings = [
            validation.message
            for validation in validations
            if validation.status == MODEL_VALIDATION_WARNING
        ]
        if (
            self._using_shared_provider_setup()
            and image_provider == prompt_provider
            and image_provider in KEYED_PROVIDERS
        ):
            if not self._api_key_for(image_provider, "image"):
                missing.append(f"{PROVIDER_LABELS[image_provider]} API key")
        else:
            if image_provider in KEYED_PROVIDERS and not self._api_key_for(image_provider, "image"):
                missing.append(f"{PROVIDER_LABELS[image_provider]} image key")
            if prompt_provider in KEYED_PROVIDERS and not self._api_key_for(prompt_provider, "prompt"):
                missing.append(f"{PROVIDER_LABELS[prompt_provider]} prompt key")
        if missing or model_errors:
            self.status_label.setText(
                "Provider setup needs: " + ", ".join([*missing, *model_errors])
            )
            return
        ready_status = (
            "Provider setup ready: "
            f"image {PROVIDER_LABELS[image_provider]} / prompt {PROVIDER_LABELS[prompt_provider]}"
        )
        if model_warnings:
            self.status_label.setText(
                "Provider setup ready with notes: "
                f"image {PROVIDER_LABELS[image_provider]} / "
                f"prompt {PROVIDER_LABELS[prompt_provider]}; "
                + "; ".join(model_warnings)
            )
            return
        self.status_label.setText(ready_status)

    def _on_save_provider_settings(self) -> None:
        if self._using_shared_provider_setup():
            self._sync_prompt_provider_from_image_provider(reset_model=False)
        settings = UserSettings(
            image_provider=self.image_provider_combo.currentData(),
            image_model=self.image_model_edit.text().strip(),
            prompt_provider=self.prompt_provider_combo.currentData(),
            prompt_model=self.prompt_model_edit.text().strip(),
            shared_provider_setup=self._using_shared_provider_setup(),
            api_keys=dict(self._user_settings.api_keys),
        )
        image_key = self.image_api_key_edit.text()
        prompt_key = self.prompt_api_key_edit.text()
        if settings.shared_provider_setup or settings.image_provider == settings.prompt_provider:
            settings.set_api_key(settings.image_provider, image_key or prompt_key)
        else:
            settings.set_api_key(settings.image_provider, image_key)
            settings.set_api_key(settings.prompt_provider, prompt_key)
        path = self._settings_store.save(settings)
        self._user_settings = settings
        self.status_label.setText(f"Saved local provider setup to {path}")
```

- [ ] **Step 9: Run the focused tests**

Run:

```bash
pytest tests/spritegen/test_desktop_ui.py::test_main_window_uses_shared_provider_setup_by_default tests/spritegen/test_desktop_ui.py::test_main_window_shared_provider_setup_saves_one_key tests/spritegen/test_desktop_ui.py::test_main_window_advanced_provider_setup_remains_available tests/spritegen/test_desktop_ui.py::test_main_window_checks_provider_setup_without_network tests/spritegen/test_desktop_ui.py::test_main_window_saves_local_provider_setup tests/spritegen/test_desktop_ui.py::test_main_window_saves_shared_provider_key_once -q
```

Expected: PASS.

- [ ] **Step 10: Commit Task 1**

Run:

```bash
git add src/spritegen/user_settings.py src/spritegen/ui/main_window.py tests/spritegen/test_desktop_ui.py
git commit -m "feat: default to shared provider setup"
```

Expected: commit succeeds.

---

### Task 2: Add A Mock-Only Try Sample Run Path

**Files:**
- Modify: `src/spritegen/ui/main_window.py:360-385`
- Modify: `src/spritegen/ui/main_window.py:1197-1228`
- Modify: `src/spritegen/ui/main_window.py:1717-1742`
- Test: `tests/spritegen/test_desktop_ui.py`

**Interfaces:**
- Consumes: `MainWindow._on_apply_project_starter() -> None`, `MainWindow._on_check_run() -> None`, `MainWindow._set_combo_value(combo: QComboBox, value: str) -> None`.
- Produces: `MainWindow._on_try_sample_run() -> None`, `MainWindow.try_sample_run_btn: QPushButton`.

- [ ] **Step 1: Write the failing sample-run test**

Append this test after the Task 1 tests in `tests/spritegen/test_desktop_ui.py`:

```python
def test_main_window_try_sample_run_creates_mock_preflight(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from PySide6.QtWidgets import QApplication
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.project_root_edit.setText(str(tmp_path / "projects"))
    window._set_combo_value(window.image_provider_combo, "openrouter")
    window._on_image_provider_changed()
    window.image_api_key_edit.setText("paid-provider-key")

    window._on_try_sample_run()

    assert window.image_provider_combo.currentData() == "mock"
    assert window.prompt_provider_combo.currentData() == "mock"
    assert window.image_api_key_edit.text() == ""
    assert window.prompt_api_key_edit.text() == ""
    assert window.generation_variants_spin.value() == 1
    assert window.project_combo.findData("myceliumtd") >= 0
    assert (tmp_path / "projects" / "myceliumtd" / "project.json").exists()
    assert (tmp_path / "projects" / "myceliumtd" / "assets" / "puffball.json").exists()

    preview = window.prompt_preview_edit.toPlainText()
    assert "Preflight:" in preview
    assert "Image model: mock / mock" in preview
    assert "Prompt enhancement: disabled" in preview
    assert "Images: 4 atlas image(s), 4 sliced sprite(s)" in preview
    assert "Sample run ready" in window.status_label.text()
    assert "Mock is selected" in window.status_label.text()

    window.close()
    app.processEvents()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/spritegen/test_desktop_ui.py::test_main_window_try_sample_run_creates_mock_preflight -q
```

Expected: FAIL because `MainWindow` has no `_on_try_sample_run`.

- [ ] **Step 3: Add the button to the starter row**

In `src/spritegen/ui/main_window.py`, inside `_create_left_panel`, find the `starter_row` block and replace it with:

```python
        starter_row = QHBoxLayout()
        self.project_starter_combo = QComboBox()
        for starter in list_project_starters():
            self.project_starter_combo.addItem(starter.label, starter.key)
        self.create_project_starter_btn = QPushButton("Create Starter")
        self.create_project_starter_btn.clicked.connect(self._on_apply_project_starter)
        self.try_sample_run_btn = QPushButton("Try Sample Run")
        self.try_sample_run_btn.clicked.connect(self._on_try_sample_run)
        starter_row.addWidget(self.project_starter_combo, 1)
        starter_row.addWidget(self.create_project_starter_btn)
        starter_row.addWidget(self.try_sample_run_btn)
        project_layout.addRow("Starter:", starter_row)
```

- [ ] **Step 4: Add the sample-run handler**

In `src/spritegen/ui/main_window.py`, add this complete method immediately after `_on_project_starter_applied` if that method exists, otherwise immediately after `_on_apply_project_starter` and before `_on_improve_project`:

```python
    def _on_try_sample_run(self) -> None:
        self.shared_provider_setup_check.setChecked(True)
        self._set_combo_value(self.image_provider_combo, "mock")
        self._on_image_provider_changed()
        self._set_combo_value(self.prompt_provider_combo, "mock")
        self._on_prompt_provider_changed()
        self.image_api_key_edit.clear()
        self.prompt_api_key_edit.clear()
        self.generation_variants_spin.setValue(1)
        self._on_apply_project_starter()
        self._on_check_run()
        self.status_label.setText(
            "Sample run ready: reviewed mock preflight; Mock is selected so Generate will not spend provider credits."
        )
```

- [ ] **Step 5: Include the button in busy-state handling**

In `src/spritegen/ui/main_window.py`, inside `_set_busy`, add this line immediately after `self.create_project_starter_btn.setEnabled(not busy)`:

```python
        self.try_sample_run_btn.setEnabled(not busy)
```

- [ ] **Step 6: Run sample-run and starter tests**

Run:

```bash
pytest tests/spritegen/test_desktop_ui.py::test_main_window_try_sample_run_creates_mock_preflight tests/spritegen/test_desktop_ui.py::test_main_window_creates_project_starter tests/spritegen/test_desktop_ui.py::test_main_window_check_run_writes_preflight_summary -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 2**

Run:

```bash
git add src/spritegen/ui/main_window.py tests/spritegen/test_desktop_ui.py
git commit -m "feat: add mock sample run path"
```

Expected: commit succeeds.

---

### Task 3: Document The Safer Desktop First Run

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 1 shared-provider mode and Task 2 `Try Sample Run`.
- Produces: README guidance for the supported first-run workflow.

- [ ] **Step 1: Update README desktop guidance**

In `README.md`, in the `## Desktop App` section, insert this paragraph immediately after the sentence that starts `On Windows, double-click`:

```markdown
For a low-risk first run, open the desktop app and use **Try Sample Run**. It creates the bundled MyceliumTD starter project, switches image and prompt providers to **Mock**, runs **Check Run**, and shows the expected atlas, slice, layout, and prompt plan shape without spending provider credits.
```

Then replace the paragraph that starts `The desktop app exposes separate provider/model fields` with this text:

```markdown
The desktop app uses one provider by default and keeps separate role-aware model fields for image generation and prompt improvement. Turn off **Use same provider for prompt improvement** only when you intentionally want different providers or API keys for those two roles. Each provider has suggested model IDs beside the editable model fields, so a user can choose a known-good default or paste a newer/custom model.
```

- [ ] **Step 2: Verify the README contains the new user path**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path("README.md").read_text(encoding="utf-8")
assert "Try Sample Run" in text
assert "Use same provider for prompt improvement" in text
assert "without spending provider credits" in text
PY
```

Expected: command exits 0.

- [ ] **Step 3: Commit Task 3**

Run:

```bash
git add README.md
git commit -m "docs: explain guided desktop first run"
```

Expected: commit succeeds.

---

### Task 4: Verification And Manual QA

**Files:**
- Verify: `src/spritegen/user_settings.py`
- Verify: `src/spritegen/ui/main_window.py`
- Verify: `tests/spritegen/test_desktop_ui.py`
- Verify: `README.md`

**Interfaces:**
- Consumes: Tasks 1-3.
- Produces: evidence that the implementation satisfies the plan.

- [ ] **Step 1: Run focused desktop tests**

Run:

```bash
pytest tests/spritegen/test_desktop_ui.py -q
```

Expected: PASS or SKIP only if PySide6 is unavailable in the environment.

- [ ] **Step 2: Run settings and provider-adjacent tests**

Run:

```bash
pytest tests/spritegen/test_provider_models.py tests/spritegen/test_projects.py -q
```

Expected: PASS.

- [ ] **Step 3: Run lint on changed Python files**

Run:

```bash
ruff check src/spritegen/user_settings.py src/spritegen/ui/main_window.py tests/spritegen/test_desktop_ui.py
```

Expected: PASS.

- [ ] **Step 4: Manually QA the desktop first-run path**

Run:

```bash
python -m spritegen.desktop
```

Expected observable behavior:
- App opens.
- `Use same provider for prompt improvement` is checked.
- Prompt provider and prompt API key fields are hidden.
- Image and prompt model fields remain visible.
- Changing `Provider` to `OpenRouter` updates both provider roles and keeps image/prompt models role-aware.
- Unchecking `Use same provider for prompt improvement` reveals prompt provider and prompt API key fields.
- Clicking `Try Sample Run` switches to `Mock`, creates the MyceliumTD/Puffball starter under the selected project directory, writes a preflight report into the prompt panel, and does not make network calls.

- [ ] **Step 5: Run mock CLI preflight as a non-GUI sanity check**

Run:

```bash
python -m spritegen.cli project preflight --project myceliumtd --asset puffball --provider mock --prompt-provider mock
```

Expected output includes:

```text
Preflight:
Project: MyceliumTD
Asset: Puffball
Image model: mock / mock
Prompt enhancement: disabled
```

- [ ] **Step 6: Commit only if verification changes were needed**

If verification required small fixes, commit them:

```bash
git add src/spritegen/user_settings.py src/spritegen/ui/main_window.py tests/spritegen/test_desktop_ui.py README.md
git commit -m "fix: polish guided provider setup"
```

Expected: commit succeeds when there are verification fixes. If no files changed after Task 3, skip this commit.

---

## Self-Review

**Spec coverage:**  
The exact SpriteGen issue #3 requirements are covered in Task 1: one provider surface by default, role-aware model fields remain visible, advanced separate providers remain available, and existing preflight/model validation remains active. The research recommendation for proof before spending tokens is covered in Task 2 with a mock-only sample preflight. README guidance is covered in Task 3. Export wizard, generation QA, and full progressive shell are explicitly separated into follow-on plans.

**Red flag scan:**  
The plan contains no deferred implementation markers. Every code-changing step includes concrete code, exact files, commands, and expected outcomes.

**Type consistency:**  
`UserSettings.shared_provider_setup` is defined in Task 1 and used by `MainWindow._apply_user_settings` and `_on_save_provider_settings`. `MainWindow._using_shared_provider_setup`, `_apply_provider_setup_mode`, `_sync_prompt_provider_from_image_provider`, and `_on_try_sample_run` are defined before tests rely on them. Existing helper names match the current code: `_set_combo_value`, `_on_apply_project_starter`, `_on_check_run`, `_refresh_model_suggestions`, `_refresh_api_key_field`, and `_api_key_for`.
