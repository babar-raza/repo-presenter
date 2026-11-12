package demo

type Widget struct {
	Name string
}

func (w *Widget) Render() {
}

func (w *Widget) hide() {
}

type helper struct {
	value int
}
