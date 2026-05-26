import { reactive, readonly } from 'vue'

export type ConfirmOptions = {
  header: string
  message: string
  acceptLabel?: string
  rejectLabel?: string
}

type ConfirmHandler = (options: ConfirmOptions) => boolean | Promise<boolean>

type ConfirmState = {
  visible: boolean
  options: ConfirmOptions
}

const defaultOptions: ConfirmOptions = {
  header: 'Please confirm',
  message: '',
  acceptLabel: 'Confirm',
  rejectLabel: 'Cancel',
}

const state = reactive<ConfirmState>({
  visible: false,
  options: defaultOptions,
})

let resolver: ((accepted: boolean) => void) | null = null
let handler: ConfirmHandler | null = null

function closeWith(value: boolean) {
  state.visible = false
  const currentResolver = resolver
  resolver = null
  currentResolver?.(value)
}

export function setConfirmHandler(nextHandler: ConfirmHandler | null) {
  handler = nextHandler
}

export function useConfirmState() {
  return readonly(state)
}

export async function confirmDanger(options: ConfirmOptions): Promise<boolean> {
  if (handler) {
    return Boolean(await handler(options))
  }
  state.options = {
    ...defaultOptions,
    ...options,
  }
  state.visible = true
  return new Promise<boolean>((resolve) => {
    resolver = resolve
  })
}

export function acceptConfirm() {
  closeWith(true)
}

export function rejectConfirm() {
  closeWith(false)
}
