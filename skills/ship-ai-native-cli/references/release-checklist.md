# Release Checklist

## Local Verification

Run before committing:

```bash
cargo fmt --all -- --check
cargo check
cargo test
cargo build --release
cargo run -- --help
```

Also run the most important real-world smoke test:

- local app/database access for local tools;
- authenticated read-only API call for API tools;
- installed binary behavior after Homebrew install.

## Makefile

Include:

```makefile
.PHONY: build check fmt test install-local install release clean

build:
	cargo build --release

check:
	cargo check

fmt:
	cargo fmt --all

test:
	cargo test

install-local: build
	mkdir -p ~/.local/bin
	cp target/release/<bin> ~/.local/bin/

install: build
	sudo cp target/release/<bin> /usr/local/bin/

release:
	scripts/release.sh

clean:
	cargo clean
	rm -f ~/.local/bin/<bin> 2>/dev/null || true
```

## CI

Use macOS arm64 when the product is macOS-specific or distributed as
`darwin-arm64`:

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
env:
  CARGO_TERM_COLOR: always
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true
jobs:
  build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions-rust-lang/setup-rust-toolchain@v1
      - name: Verify arm64 runner
        run: test "$(uname -m)" = "arm64"
      - name: Format
        run: cargo fmt --all -- --check
      - name: Build
        run: cargo build --release
      - name: Test
        run: cargo test
      - name: Verify CLI
        run: cargo run --release -- --help
```

## Release Workflow

On tag `v*`:

1. Build release binary on `macos-latest`.
2. Archive `target/release/<bin>` into `<bin>-${{ github.ref_name }}-darwin-arm64.tar.gz`.
3. Upload artifact.
4. Create GitHub release with `softprops/action-gh-release@v2`.

## Homebrew Formula Rules

Prefer prebuilt release assets:

```ruby
class Tool < Formula
  desc "..."
  homepage "https://github.com/<owner>/<repo>"
  url "https://github.com/<owner>/<repo>/releases/download/vX.Y.Z/tool-vX.Y.Z-darwin-arm64.tar.gz"
  sha256 "..."
  license "MIT"

  depends_on arch: :arm64

  head do
    url "https://github.com/<owner>/<repo>.git", branch: "main"
    depends_on "rust" => :build
  end

  def install
    if build.head?
      system "cargo", "install", "--bin", "tool", "--root", prefix, "."
    else
      bin.install "tool"
    end
  end

  test do
    system bin/"tool", "--help"
  end
end
```

Avoid requiring Rust for normal `brew install`; only `--HEAD` should build from
source.

## Release Script Behavior

The release script should:

1. Refuse dirty source and dirty tap checkouts.
2. Pull tap and fetch source tags.
3. Bump `Cargo.toml` and `Cargo.lock` when requested.
4. Run tests.
5. Push main and tag.
6. Wait for GitHub Actions release.
7. Read or compute asset sha256.
8. Update `Formula/<bin>.rb` in the tap and push it.
9. Run `brew update`, `brew upgrade/reinstall`, and `brew test`.

Do not call the release complete until `brew test` passes.
