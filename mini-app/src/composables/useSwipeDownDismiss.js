/**
 * Свайп вниз для закрытия (шторки, полноэкранный плеер).
 */
export function useSwipeDownDismiss(onDismiss, options = {}) {
  const threshold = options.threshold ?? 100
  let startY = 0
  let tracking = false

  function touchStart(e) {
    startY = e.touches[0].clientY
    tracking = true
  }

  function touchMove(e) {
    if (!tracking) return
    const dy = e.touches[0].clientY - startY
    if (dy > threshold) {
      onDismiss()
      tracking = false
    }
  }

  function touchEnd() {
    tracking = false
  }

  function mouseDown(e) {
    if (e.button !== 0) return
    startY = e.clientY
    tracking = true
    document.addEventListener('mousemove', mouseMove)
    document.addEventListener('mouseup', mouseUp)
  }

  function mouseMove(e) {
    if (!tracking) return
    const dy = e.clientY - startY
    if (dy > threshold) {
      onDismiss()
      tracking = false
      document.removeEventListener('mousemove', mouseMove)
      document.removeEventListener('mouseup', mouseUp)
    }
  }

  function mouseUp() {
    tracking = false
    document.removeEventListener('mousemove', mouseMove)
    document.removeEventListener('mouseup', mouseUp)
  }

  return { touchStart, touchMove, touchEnd, mouseDown, mouseMove, mouseUp }
}

/**
 * Закрытие при «потягивании» вниз, когда скролл вверху (scrollTop ≈ 0).
 * touch должен начаться в верхней зоне контейнера (topZonePx от верха).
 */
export function usePullDownFromTopOfScroll(scrollRef, onDismiss, options = {}) {
  const threshold = options.threshold ?? 120
  const topZonePx = options.topZonePx ?? 240
  let startY = 0
  let tracking = false

  function touchStart(e) {
    const el = scrollRef.value
    if (!el) return
    if (el.scrollTop > 12) return
    const rect = el.getBoundingClientRect()
    const localY = e.touches[0].clientY - rect.top
    if (localY > topZonePx) return
    startY = e.touches[0].clientY
    tracking = true
  }

  function touchMove(e) {
    if (!tracking) return
    const el = scrollRef.value
    if (!el || el.scrollTop > 12) {
      tracking = false
      return
    }
    const dy = e.touches[0].clientY - startY
    if (dy > threshold) {
      onDismiss()
      tracking = false
    }
  }

  function touchEnd() {
    tracking = false
  }

  function mouseDown(e) {
    if (e.button !== 0) return
    const el = scrollRef.value
    if (!el) return
    if (el.scrollTop > 12) return
    const rect = el.getBoundingClientRect()
    const localY = e.clientY - rect.top
    if (localY > topZonePx) return
    startY = e.clientY
    tracking = true
    document.addEventListener('mousemove', mouseMove)
    document.addEventListener('mouseup', mouseUp)
  }

  function mouseMove(e) {
    if (!tracking) return
    const el = scrollRef.value
    if (!el || el.scrollTop > 12) {
      tracking = false
      document.removeEventListener('mousemove', mouseMove)
      document.removeEventListener('mouseup', mouseUp)
      return
    }
    const dy = e.clientY - startY
    if (dy > threshold) {
      onDismiss()
      tracking = false
      document.removeEventListener('mousemove', mouseMove)
      document.removeEventListener('mouseup', mouseUp)
    }
  }

  function mouseUp() {
    tracking = false
    document.removeEventListener('mousemove', mouseMove)
    document.removeEventListener('mouseup', mouseUp)
  }

  return { touchStart, touchMove, touchEnd, mouseDown, mouseMove, mouseUp }
}
