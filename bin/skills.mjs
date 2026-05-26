#!/usr/bin/env node
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const SKILLS_DIR = path.join(ROOT, 'skills')
const TARGETS = {
  codex: path.join(os.homedir(), '.codex', 'skills'),
  agents: path.join(os.homedir(), '.agents', 'skills'),
  claude: path.join(os.homedir(), '.claude', 'skills'),
}

function main(argv) {
  const [command, ...rest] = argv
  switch (command) {
    case undefined:
    case '-h':
    case '--help':
    case 'help':
      printHelp()
      return
    case 'list':
      listSkills()
      return
    case 'install':
    case 'add':
      install(rest)
      return
    default:
      install(argv)
  }
}

function printHelp() {
  console.log(`xiaotianxt-skills

Usage:
  npx @xiaotianxt/skills list
  npx @xiaotianxt/skills bro-browser
  npx @xiaotianxt/skills tg --target agents
  npx @xiaotianxt/skills install cx --target codex

Options:
  --target <codex|agents|claude>  Install target. Default: codex.
  --dir <path>                    Override install directory.
  --dry-run                       Print actions without writing.
  --force                         Replace existing skill without backup.

Installs exactly one named skill. There is intentionally no "install all" mode.
`)
}

function listSkills() {
  for (const skill of availableSkills()) {
    console.log(skill)
  }
}

function install(args) {
  const options = parseInstallArgs(args)
  if (options.skills.length === 0) {
    fail('install requires exactly one skill name')
  }
  if (options.skills.length > 1) {
    fail('install accepts one skill name; run separate commands for separate skills')
  }

  const targets = resolveTargets(options)
  for (const skill of options.skills) {
    assertSkillExists(skill)
  }

  for (const target of targets) {
    for (const skill of options.skills) {
      installSkill(skill, target, options)
    }
  }
}

function parseInstallArgs(args) {
  const options = {
    dryRun: false,
    force: false,
    target: 'codex',
    dir: undefined,
    skills: [],
  }

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i]
    if (arg === '--dry-run') {
      options.dryRun = true
    } else if (arg === '--force') {
      options.force = true
    } else if (arg === '--target') {
      options.target = requireValue(args, ++i, '--target')
    } else if (arg.startsWith('--target=')) {
      options.target = arg.slice('--target='.length)
    } else if (arg === '--dir') {
      options.dir = requireValue(args, ++i, '--dir')
    } else if (arg.startsWith('--dir=')) {
      options.dir = arg.slice('--dir='.length)
    } else if (arg.startsWith('-')) {
      fail(`unknown option: ${arg}`)
    } else {
      options.skills.push(arg)
    }
  }

  return options
}

function requireValue(args, index, option) {
  const value = args[index]
  if (!value || value.startsWith('-')) {
    fail(`${option} requires a value`)
  }
  return value
}

function resolveTargets(options) {
  if (options.dir) {
    return [path.resolve(expandHome(options.dir))]
  }
  const target = TARGETS[options.target]
  if (!target) {
    fail('--target must be codex, agents, or claude')
  }
  return [target]
}

function availableSkills() {
  return fs
    .readdirSync(SKILLS_DIR, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .filter((name) => fs.existsSync(path.join(SKILLS_DIR, name, 'SKILL.md')))
    .sort()
}

function assertSkillExists(skill) {
  if (!/^[a-z0-9][a-z0-9-]*$/.test(skill)) {
    fail(`invalid skill name: ${skill}`)
  }
  const src = path.join(SKILLS_DIR, skill)
  if (!fs.existsSync(path.join(src, 'SKILL.md'))) {
    fail(`unknown skill: ${skill}`)
  }
}

function installSkill(skill, targetDir, options) {
  const src = path.join(SKILLS_DIR, skill)
  const dest = path.join(targetDir, skill)

  if (skill === 'tg') {
    console.error(
      'note: `tg skill install` renders the local machine-specific tg skill; this installer copies the public Telegram-worded template.',
    )
  }

  if (fs.existsSync(dest) || isSymlink(dest)) {
    const current = describeExisting(dest)
    if (current === src) {
      console.log(`ok ${dest} -> ${src}`)
      return
    }

    if (options.force) {
      log(options, `remove ${dest}`)
      if (!options.dryRun) fs.rmSync(dest, { recursive: true, force: true })
    } else {
      const backup = backupPath(targetDir, skill)
      log(options, `backup ${dest} -> ${backup}`)
      if (!options.dryRun) {
        fs.mkdirSync(path.dirname(backup), { recursive: true })
        fs.renameSync(dest, backup)
      }
    }
  }

  log(options, `copy ${dest} <- ${src}`)
  if (options.dryRun) return
  fs.mkdirSync(targetDir, { recursive: true })
  fs.cpSync(src, dest, {
    recursive: true,
    filter: (source) => !shouldSkip(path.basename(source)),
  })
}

function describeExisting(dest) {
  try {
    const stat = fs.lstatSync(dest)
    if (stat.isSymbolicLink()) {
      return path.resolve(path.dirname(dest), fs.readlinkSync(dest))
    }
    return 'directory'
  } catch {
    return undefined
  }
}

function isSymlink(dest) {
  try {
    return fs.lstatSync(dest).isSymbolicLink()
  } catch {
    return false
  }
}

function backupPath(targetDir, skill) {
  const stamp = new Date()
    .toISOString()
    .replaceAll('-', '')
    .replaceAll(':', '')
    .replace(/\..+$/, '')
  return path.join(targetDir, `.skills-backup-${stamp}`, skill)
}

function shouldSkip(name) {
  return name === '.DS_Store' || name === '__pycache__' || name.endsWith('.pyc')
}

function expandHome(value) {
  if (value === '~') return os.homedir()
  if (value.startsWith('~/')) return path.join(os.homedir(), value.slice(2))
  return value
}

function log(options, message) {
  console.log(options.dryRun ? `dry-run ${message}` : message)
}

function fail(message) {
  console.error(`error: ${message}`)
  process.exit(1)
}

main(process.argv.slice(2))
