"/apps/{appSlug}/human-review/jobs": {
      "get": {
        "responses": {
          "200": {
            "description": "The jobs were returned successfully",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "jobs": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "id": {
                            "type": "string"
                          },
                          "name": {
                            "type": "string"
                          },
                          "reviewer": {
                            "type": "object",
                            "properties": {
                              "email": {
                                "type": "string"
                              }
                            },
                            "required": [
                              "email"
                            ]
                          }
                        },
                        "required": [
                          "id",
                          "name",
                          "reviewer"
                        ]
                      },
                      "description": "A list of jobs",
                      "example": [
                        {
                          "id": "cm83i1gtw00000cle3nf0gmtw",
                          "name": "Review for accuracy",
                          "reviewer": {
                            "email": "john@example.com"
                          }
                        }
                      ]
                    }
                  },
                  "required": [
                    "jobs"
                  ]
                }
              }
            }
          }
        },
        "operationId": "getAppsByAppSlugHuman-reviewJobs",
        "tags": [
          "Human Review"
        ],
        "parameters": [
          {
            "schema": {
              "type": "string"
            },
            "in": "path",
            "name": "appSlug",
            "required": true
          }
        ],
        "description": "Get all jobs for the app",
        "summary": "Get all jobs for the app"
      }
    },
    "/apps/{appSlug}/human-review/jobs/{jobId}": {
      "get": {
        "responses": {
          "200": {
            "description": "The job was returned successfully",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "id": {
                      "type": "string"
                    },
                    "name": {
                      "type": "string"
                    },
                    "reviewer": {
                      "type": "object",
                      "properties": {
                        "email": {
                          "type": "string"
                        }
                      },
                      "required": [
                        "email"
                      ]
                    },
                    "scores": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "id": {
                            "type": "string"
                          },
                          "name": {
                            "type": "string"
                          },
                          "description": {
                            "type": "string"
                          },
                          "options": {
                            "oneOf": [
                              {
                                "type": "object",
                                "properties": {
                                  "type": {
                                    "type": "string",
                                    "const": "binary"
                                  }
                                },
                                "required": [
                                  "type"
                                ]
                              },
                              {
                                "type": "object",
                                "properties": {
                                  "type": {
                                    "type": "string",
                                    "const": "discreteRange"
                                  },
                                  "min": {
                                    "type": "integer"
                                  },
                                  "max": {
                                    "type": "integer"
                                  },
                                  "description": {
                                    "type": "object",
                                    "additionalProperties": {
                                      "type": "string"
                                    }
                                  }
                                },
                                "required": [
                                  "type",
                                  "min",
                                  "max"
                                ]
                              },
                              {
                                "type": "object",
                                "properties": {
                                  "type": {
                                    "type": "string",
                                    "const": "tag"
                                  }
                                },
                                "required": [
                                  "type"
                                ]
                              }
                            ]
                          }
                        },
                        "required": [
                          "id",
                          "name",
                          "description",
                          "options"
                        ]
                      }
                    },
                    "items": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "id": {
                            "type": "string"
                          }
                        },
                        "required": [
                          "id"
                        ]
                      }
                    }
                  },
                  "required": [
                    "id",
                    "name",
                    "reviewer",
                    "scores",
                    "items"
                  ],
                  "description": "A job",
                  "example": {
                    "id": "cm83i1gtw00000cle3nf0gmtw",
                    "name": "Review for accuracy",
                    "reviewer": {
                      "email": "john@example.com"
                    },
                    "scores": [
                      {
                        "id": "cm83i1gtw00000cle3nf0gmtw",
                        "name": "Accuracy",
                        "description": "How accurate is the output?",
                        "options": {
                          "type": "binary"
                        }
                      }
                    ],
                    "items": [
                      {
                        "id": "cm83i1gtw00000cle3nf0gmtw"
                      }
                    ]
                  }
                }
              }
            }
          }
        },
        "operationId": "getAppsByAppSlugHuman-reviewJobsByJobId",
        "tags": [
          "Human Review"
        ],
        "parameters": [
          {
            "schema": {
              "type": "string"
            },
            "in": "path",
            "name": "appSlug",
            "required": true
          },
          {
            "schema": {
              "type": "string"
            },
            "in": "path",
            "name": "jobId",
            "required": true
          }
        ],
        "description": "Get a specific job by ID",
        "summary": "Get a specific job"
      }
    },
    "/apps/{appSlug}/human-review/jobs/{jobId}/items/{itemId}": {
      "get": {
        "responses": {
          "200": {
            "description": "The job item was returned successfully",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "id": {
                      "type": "string"
                    },
                    "grades": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "scoreId": {
                            "type": "string"
                          },
                          "grade": {
                            "type": "number"
                          },
                          "user": {
                            "type": "object",
                            "properties": {
                              "email": {
                                "type": "string"
                              }
                            },
                            "required": [
                              "email"
                            ]
                          }
                        },
                        "required": [
                          "scoreId",
                          "grade",
                          "user"
                        ]
                      }
                    },
                    "inputFields": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "id": {
                            "type": "string"
                          },
                          "name": {
                            "type": "string"
                          },
                          "value": {
                            "type": "string"
                          },
                          "contentType": {
                            "type": "string",
                            "enum": [
                              "TEXT",
                              "MARKDOWN",
                              "HTML",
                              "LINK"
                            ]
                          }
                        },
                        "required": [
                          "id",
                          "name",
                          "value",
                          "contentType"
                        ]
                      }
                    },
                    "outputFields": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "id": {
                            "type": "string"
                          },
                          "name": {
                            "type": "string"
                          },
                          "value": {
                            "type": "string"
                          },
                          "contentType": {
                            "type": "string",
                            "enum": [
                              "TEXT",
                              "MARKDOWN",
                              "HTML",
                              "LINK"
                            ]
                          }
                        },
                        "required": [
                          "id",
                          "name",
                          "value",
                          "contentType"
                        ]
                      }
                    },
                    "fieldComments": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "fieldId": {
                            "type": "string"
                          },
                          "startIdx": {
                            "type": "number"
                          },
                          "endIdx": {
                            "type": "number"
                          },
                          "value": {
                            "type": "string"
                          },
                          "inRelationToScoreName": {
                            "type": "string"
                          },
                          "user": {
                            "type": "object",
                            "properties": {
                              "email": {
                                "type": "string"
                              }
                            },
                            "required": [
                              "email"
                            ]
                          }
                        },
                        "required": [
                          "fieldId",
                          "value",
                          "user"
                        ]
                      }
                    },
                    "inputComments": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "value": {
                            "type": "string"
                          },
                          "inRelationToScoreName": {
                            "type": "string"
                          },
                          "user": {
                            "type": "object",
                            "properties": {
                              "email": {
                                "type": "string"
                              }
                            },
                            "required": [
                              "email"
                            ]
                          }
                        },
                        "required": [
                          "value",
                          "user"
                        ]
                      }
                    },
                    "outputComments": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "value": {
                            "type": "string"
                          },
                          "inRelationToScoreName": {
                            "type": "string"
                          },
                          "user": {
                            "type": "object",
                            "properties": {
                              "email": {
                                "type": "string"
                              }
                            },
                            "required": [
                              "email"
                            ]
                          }
                        },
                        "required": [
                          "value",
                          "user"
                        ]
                      }
                    }
                  },
                  "required": [
                    "id",
                    "grades",
                    "inputFields",
                    "outputFields",
                    "fieldComments",
                    "inputComments",
                    "outputComments"
                  ],
                  "description": "A job item",
                  "example": {
                    "id": "cm83i1gtw00000cle3nf0gmtw",
                    "grades": [
                      {
                        "scoreId": "cm83i1gtw00000cle3nf0gmtw",
                        "grade": 0.5,
                        "user": {
                          "email": "john@example.com"
                        }
                      }
                    ],
                    "inputFields": [
                      {
                        "id": "cm83i1gtw00000cle3nf0gmtw",
                        "name": "input",
                        "value": "Hello, world!",
                        "contentType": "TEXT"
                      }
                    ],
                    "outputFields": [
                      {
                        "id": "cm83i1gtw00000cle3nf0gmtw",
                        "name": "output",
                        "value": "Hello, world!",
                        "contentType": "TEXT"
                      }
                    ],
                    "fieldComments": [
                      {
                        "fieldId": "cm83i1gtw00000cle3nf0gmtw",
                        "value": "This is a comment",
                        "startIdx": 1,
                        "endIdx": 2,
                        "inRelationToScoreName": "accuracy",
                        "user": {
                          "email": "john@example.com"
                        }
                      }
                    ],
                    "inputComments": [
                      {
                        "value": "This is a comment",
                        "inRelationToScoreName": "accuracy",
                        "user": {
                          "email": "john@example.com"
                        }
                      }
                    ],
                    "outputComments": [
                      {
                        "value": "This is a comment",
                        "inRelationToScoreName": "accuracy",
                        "user": {
                          "email": "john@example.com"
                        }
                      }
                    ]
                  }
                }
              }
            }
          }
        },
        "operationId": "getAppsByAppSlugHuman-reviewJobsByJobIdItemsByItemId",
        "tags": [
          "Human Review"
        ],
        "parameters": [
          {
            "schema": {
              "type": "string"
            },
            "in": "path",
            "name": "appSlug",
            "required": true
          },
          {
            "schema": {
              "type": "string"
            },
            "in": "path",
            "name": "jobId",
            "required": true
          },
          {
            "schema": {
              "type": "string"
            },
            "in": "path",
            "name": "itemId",
            "required": true
          }
        ],
        "description": "Get a specific job item by ID",
        "summary": "Get a specific job item"
      }
    }
  }
