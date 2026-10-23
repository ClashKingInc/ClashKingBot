import { commandDefinitions } from "../src/commands/registry";
import type { ApplicationCommandOption } from "../src/commands/types";

const errors: string[] = [];
const names = new Set<string>();

if (commandDefinitions.length > 100) {
  errors.push(`global command count ${commandDefinitions.length} exceeds Discord's limit of 100`);
}

for (const command of commandDefinitions) {
  if (names.has(command.name)) {
    errors.push(`duplicate command ${command.name}`);
  }
  names.add(command.name);
  validateName(command.name, command.name);
  validateDescription(command.name, command.description);
  for (const [locale, name] of Object.entries(command.name_localizations ?? {})) validateName(`${command.name}/${locale}`, name);
  for (const [locale, description] of Object.entries(command.description_localizations ?? {})) validateDescription(`${command.name}/${locale}`, description);
  validateOptions(command.name, command.options ?? []);
}

if (errors.length > 0) {
  throw new Error(`Command validation failed:\n${errors.join("\n")}`);
}

console.log(`Validated ${commandDefinitions.length} global command definition(s)`);

function validateOptions(parent: string, options: ApplicationCommandOption[]): void {
  if (options.length > 25) {
    errors.push(`${parent} has ${options.length} options; maximum is 25`);
  }
  let optionalSeen = false;
  for (const option of options) {
    const path = `${parent} ${option.name}`;
    validateName(path, option.name);
    validateDescription(path, option.description);
    for (const [locale, name] of Object.entries(option.name_localizations ?? {})) validateName(`${path}/${locale}`, name);
    for (const [locale, description] of Object.entries(option.description_localizations ?? {})) validateDescription(`${path}/${locale}`, description);
    if (option.required === false || option.required === undefined) {
      optionalSeen = true;
    } else if (optionalSeen) {
      errors.push(`${path} is required after an optional sibling`);
    }
    if (option.options) {
      validateOptions(path, option.options);
    }
  }
}

function validateName(path: string, name: string): void {
  if ([...name].length > 32 || !/^[-_\p{L}\p{M}\p{N}]+$/u.test(name) || name !== name.toLowerCase()) {
    errors.push(`${path} has invalid name ${JSON.stringify(name)}`);
  }
}

function validateDescription(path: string, description: string): void {
  if (description.length < 1 || description.length > 100) {
    errors.push(`${path} description length is ${description.length}; expected 1-100`);
  }
}
