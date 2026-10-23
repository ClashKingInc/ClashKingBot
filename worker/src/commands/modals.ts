import type { ModalComponent } from "../discord/types";

/** Accept current Label wrappers and already-published legacy Action Rows. */
export function modalFields(components: ModalComponent[] = []): Map<string, ModalComponent> {
  const fields = new Map<string, ModalComponent>();
  const visit = (component: ModalComponent): void => {
    if (component.custom_id) fields.set(component.custom_id, component);
    if (component.component) visit(component.component);
    component.components?.forEach(visit);
  };
  components.forEach(visit);
  return fields;
}

export function textField(id: string, label: string, maxLength: number, paragraph = false) {
  return { type: 18, label, component: {
    type: 4, custom_id: id, style: paragraph ? 2 : 1, required: true, min_length: 1, max_length: maxLength,
  } };
}
