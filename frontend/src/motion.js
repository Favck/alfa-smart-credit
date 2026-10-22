const selector = [
  '.card',
  '.banner',
  '.home-greeting',
  '.section-title',
  '.entry-panel',
  '.welcome-copy > :not(.finance-art)',
].join(', ')

// Unenhanced content remains visible if motion is disabled or unsupported.
export const reveal = {
  mounted(element) {
    if (
      window.matchMedia('(prefers-reduced-motion: reduce)').matches ||
      !('IntersectionObserver' in window)
    )
      return
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          entry.target.classList.add('is-revealed')
          observer.unobserve(entry.target)
        }
      },
      { threshold: 0.08 },
    )
    element.querySelectorAll(selector).forEach((target, index) => {
      if (target.classList.contains('news-card')) return
      target.style.setProperty('--reveal-delay', `${(index % 3) * 65}ms`)
      target.classList.add('reveal-target')
      observer.observe(target)
    })
    element.motionObserver = observer
  },
  beforeUnmount(element) {
    element.motionObserver?.disconnect()
  },
}
