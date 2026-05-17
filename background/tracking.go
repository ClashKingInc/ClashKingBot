package background

import (
	"net/http"

	"go.mongodb.org/mongo-driver/v2/mongo"
)

type Provider interface {
	getTags() []string
	getItem(tag string)
	cache(tag string)
	bulkCache(tags []string)
}
type Tracking struct {
	database *mongo.Client
	baseUrl  string
	tags     []string

	httpClient *http.Client
	batchSize  int
	provider   Provider

	structType any

	results chan string
}

func (t *Tracking) trackItem(tag string) {
	resp, err := t.httpClient.Get(t.baseUrl + "/clan/" + tag)
	if err != nil {
		// check status codes
		return
	}
	defer resp.Body.Close()

}

func (t *Tracking) track() {
	t.tags = t.provider.getTags()
	for _, tag := range t.tags {
		tag := tag
		go t.trackItem(tag)
	}
}

func (t *Tracking) removeFromWorkers() {

}
