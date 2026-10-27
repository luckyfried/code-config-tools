// Canvas confetti with gravity, drag, and spin: paper rectangles that tumble (their visible width follows a cosine
// of the flip angle) and fall out of the window. One burst per call, fired in a fan around `aim` (radians, -PI/2 is
// straight up); the canvas removes itself when the last piece is gone.

type Piece = { x: number; y: number; vx: number; vy: number; rot: number; spin: number; flip: number; flipSpeed: number; w: number; h: number; color: string }

export function burst(origin: { x: number; y: number }, colors: string[], count: number, aim = -Math.PI / 2) {
  const canvas = document.createElement("canvas")
  canvas.setAttribute("aria-hidden", "true")
  canvas.className = "pointer-events-none fixed inset-0 z-50 size-full"
  document.body.appendChild(canvas)
  const ctx = canvas.getContext("2d")
  if (!ctx) {
    canvas.remove()
    return
  }
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const resize = () => {
    canvas.width = window.innerWidth * dpr
    canvas.height = window.innerHeight * dpr
  }
  resize()

  const pieces: Piece[] = []
  for (let i = 0; i < count; i++) {
    const angle = aim + (Math.random() - 0.5) * Math.PI * 0.4
    const speed = 7 + Math.random() * 11
    pieces.push({
      x: origin.x + (Math.random() - 0.5) * 24,
      y: origin.y + (Math.random() - 0.5) * 30,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      rot: Math.random() * Math.PI * 2,
      spin: (Math.random() - 0.5) * 0.35,
      flip: Math.random() * Math.PI * 2,
      flipSpeed: 0.08 + Math.random() * 0.18,
      w: 6 + Math.random() * 7,
      h: 9 + Math.random() * 9,
      color: colors[i % colors.length],
    })
  }

  const gravity = 0.32
  const drag = 0.985
  let last = performance.now()
  const frame = (now: number) => {
    const dt = Math.min(2.5, (now - last) / 16.67)
    last = now
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight)
    let alive = 0
    for (const p of pieces) {
      p.vx *= drag ** dt
      p.vy = p.vy * drag ** dt + gravity * dt
      p.x += p.vx * dt + Math.sin(p.flip) * 0.6
      p.y += p.vy * dt
      p.rot += p.spin * dt
      p.flip += p.flipSpeed * dt
      if (p.y > window.innerHeight + 40) continue
      alive++
      ctx.save()
      ctx.translate(p.x, p.y)
      ctx.rotate(p.rot)
      ctx.scale(Math.cos(p.flip), 1)
      ctx.fillStyle = p.color
      ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h)
      ctx.restore()
    }
    if (alive > 0) requestAnimationFrame(frame)
    else {
      window.removeEventListener("resize", resize)
      canvas.remove()
    }
  }
  window.addEventListener("resize", resize)
  requestAnimationFrame(frame)
}
