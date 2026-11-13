package main

import (
	"fmt"
)

func main() {
	fmt.Println("MF_LOG_ROTATION_FIRST_MARKER")
	payload := "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	for i := 0; i < 6000; i++ {
		fmt.Printf("MF_LOG_LINE_%06d %s\n", i, payload)
	}
	fmt.Println("MF_LOG_ROTATION_LAST_MARKER")
}
