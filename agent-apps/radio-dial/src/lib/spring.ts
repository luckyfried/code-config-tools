// A damped spring stepped once per frame: the needle and the VU needles both ride one.
export class Spring {
  value: number
  velocity = 0
  target: number
  stiffness: number
  damping: number
  constructor(value: number, stiffness = 120, damping = 15) {
    this.value = value
    this.target = value
    this.stiffness = stiffness
    this.damping = damping
  }
  step(dt: number) {
    const h = Math.min(dt, 1 / 30)
    const force = (this.target - this.value) * this.stiffness - this.velocity * this.damping
    this.velocity += force * h
    this.value += this.velocity * h
    return this.value
  }
  snap(v: number) {
    this.value = v
    this.target = v
    this.velocity = 0
  }
  get settled() {
    return Math.abs(this.target - this.value) < 0.0015 && Math.abs(this.velocity) < 0.01
  }
}
